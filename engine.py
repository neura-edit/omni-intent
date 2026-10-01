import os
import json
import time
import numpy as np

class DecisionEngine:
    def __init__(self, model_dir=None):
        from tokenizers import Tokenizer
        import onnxruntime as ort

        if not model_dir or not os.path.exists(model_dir):
            try:
                from modelscope.hub.snapshot_download import snapshot_download
                print("[DecisionEngine] Downloading model snapshot from ModelScope: neuraedit/decision-eos...")
                model_dir = snapshot_download('neuraedit/decision-eos')
                print(f"[DecisionEngine] Downloaded to {model_dir}")
            except Exception as e:
                print(f"[DecisionEngine] ModelScope snapshot download exception: {e}")
                local_blobs = os.path.expanduser('~/.ollaya/models/blobs')
                if os.path.exists(local_blobs):
                    model_dir = local_blobs

        self.model_dir = model_dir
        onnx_file = os.path.join(model_dir, 'model.onnx')
        if not os.path.exists(onnx_file):
            onnx_file = os.path.join(model_dir, 'sha256-7917445d40c79ba330d0ff926a85401532088b29e463f86cd48417e86a53c06c')

        tok_file = os.path.join(model_dir, 'tokenizer.json')
        if not os.path.exists(tok_file):
            tok_file = os.path.join(model_dir, 'sha256-06b9509352d2af50381ab2247e083b80d32d5c0aba91c272ca9ff729b6a0e523')

        self.tokenizer = Tokenizer.from_file(tok_file)

        backbone_weights = os.path.join(model_dir, 'sha256-613f491da2794c5d22f68e81bd2d41000c5675bc4538180148e6e453e8198abd')
        if not os.path.exists(backbone_weights):
            print(f"[DecisionEngine] Backbone weights missing at {backbone_weights}, downloading from mirror...")
            try:
                import urllib.request
                url = "https://hf-mirror.com/llm-semantic-router/Decision-1.0-Eos-0.8B/resolve/3c2d632609ceb66f3a13bbc5f77f3ab8cdeebcdd/backbone/model.safetensors"
                urllib.request.urlretrieve(url, backbone_weights)
                print("[DecisionEngine] Downloaded backbone weights successfully from mirror!")
            except Exception as e:
                print(f"[DecisionEngine] Mirror download exception: {e}")

        sess_options = ort.SessionOptions()
        sess_options.intra_op_num_threads = min(8, os.cpu_count() or 4)
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.session = ort.InferenceSession(onnx_file, sess_options)
        self.temperature = 1.0389139156246665
        self.pad_id = 248044
        print(f"[DecisionEngine] Successfully initialized neural engine from {model_dir}")

    def decide(self, state, questions):
        """
        Execute batch forward pass matching the Decision 1.0 Eos neural architecture.
        """
        t0 = time.perf_counter()
        q_keys = list(questions.keys())
        if not q_keys:
            return {"answers": {}, "total_duration": 0, "usage": {"input_tokens": 0}}

        rows_tokens = []
        rows_query_pos = []
        rows_cand_pos = []
        row_metadata = []

        total_input_tokens = 0

        for q_id in q_keys:
            q_info = questions[q_id]
            q_type = q_info.get("type", "noul")
            q_inst = q_info.get("instructions", "")

            prefix_str = f"Context:\n{state}\n\nTask type: {q_type}\nQuestion:\n{q_inst}\nOptions:"
            tokens = list(self.tokenizer.encode(prefix_str, add_special_tokens=False).ids)
            cand_pos = []

            if q_type == "noul":
                options = [
                    ("false", "The answer to the question is no."),
                    ("true", "The answer to the question is yes.")
                ]
                opt_keys = ["false", "true"]
            elif q_type == "choice":
                criteria = q_info.get("criteria", {})
                options = [(k, desc) for k, desc in criteria.items()]
                opt_keys = [k for k, _ in options]
            else:
                options = [("false", "No"), ("true", "Yes")]
                opt_keys = ["false", "true"]

            for k, desc in options:
                opt_json = json.dumps({"description": desc, "key": k}, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
                opt_str = f"\n<option>\n{opt_json}\n</option>"
                opt_toks = self.tokenizer.encode(opt_str, add_special_tokens=False).ids
                tokens.extend(opt_toks)
                cand_pos.append(len(tokens) - 1)

            suffix_str = "\n\nSelect the single option best supported by the context and instructions.\nDecision:"
            tokens.extend(self.tokenizer.encode(suffix_str, add_special_tokens=False).ids)
            query_pos = len(tokens) - 1

            total_input_tokens += len(tokens)
            rows_tokens.append(tokens)
            rows_query_pos.append(query_pos)
            rows_cand_pos.append(cand_pos)
            row_metadata.append((q_id, q_type, opt_keys))

        B = len(rows_tokens)
        max_len = max(len(t) for t in rows_tokens)
        seq_len = ((max_len + 63) // 64) * 64
        max_k = max(len(c) for c in rows_cand_pos)

        input_ids = np.full((B, seq_len), self.pad_id, dtype=np.int64)
        cand_pos_arr = np.zeros((B, max_k), dtype=np.int64)
        query_pos_arr = np.array(rows_query_pos, dtype=np.int64)

        for i in range(B):
            input_ids[i, :len(rows_tokens[i])] = rows_tokens[i]
            cand_pos_arr[i, :len(rows_cand_pos[i])] = rows_cand_pos[i]

        out = self.session.run(None, {
            'input_ids': input_ids,
            'query_pos': query_pos_arr,
            'cand_pos': cand_pos_arr
        })
        raw_logits = out[0]

        answers = {}
        for i, (q_id, q_type, opt_keys) in enumerate(row_metadata):
            k_len = len(opt_keys)
            q_logits = raw_logits[i, :k_len]
            scaled = q_logits / self.temperature
            exp_logits = np.exp(scaled - np.max(scaled))
            probs = exp_logits / np.sum(exp_logits)

            if q_type == "noul":
                prob_true = float(probs[1]) if len(probs) > 1 else 0.0
                answers[q_id] = {
                    "type": "noul",
                    "noul": round(prob_true, 4)
                }
            elif q_type == "choice":
                prob_dict = {k: round(float(p), 4) for k, p in zip(opt_keys, probs)}
                best_idx = int(np.argmax(probs))
                best_k = opt_keys[best_idx]
                answers[q_id] = {
                    "type": "choice",
                    "choice": best_k,
                    "confidence": round(float(probs[best_idx]), 4),
                    "probabilities": prob_dict
                }

        wall_ms = (time.perf_counter() - t0) * 1000
        return {
            "answers": answers,
            "total_duration": int(wall_ms * 1e6),
            "usage": {"input_tokens": total_input_tokens}
        }
