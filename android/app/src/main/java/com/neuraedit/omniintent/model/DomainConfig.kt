package com.neuraedit.omniintent.model

data class DomainItem(
    val id: String,
    val name: String,
    val description: String,
    val isMultiLabel: Boolean = true,
    val isEnabled: Boolean = true,
    val isCustom: Boolean = false
) {
    companion object {
        fun defaultDomains(): List<DomainItem> = listOf(
            DomainItem(
                id = "climate",
                name = "空调温控",
                description = "车内温度/风速调节、除雾除霜、内外循环",
                isMultiLabel = true
            ),
            DomainItem(
                id = "music",
                name = "媒体音乐",
                description = "音乐播放、曲名/歌手搜索、曲风推荐",
                isMultiLabel = true
            ),
            DomainItem(
                id = "navigation",
                name = "导航地图",
                description = "目的地检索、路线规划、规避高速/拥堵",
                isMultiLabel = true
            ),
            DomainItem(
                id = "seat",
                name = "座椅调节",
                description = "主副驾座椅加热、通风、按摩档位切换",
                isMultiLabel = true
            ),
            DomainItem(
                id = "window",
                name = "车窗天窗",
                description = "升降车窗、打开天窗/遮阳帘、微开通风",
                isMultiLabel = true
            ),
            DomainItem(
                id = "phone",
                name = "车机电话",
                description = "蓝牙拨号、联系人查找、接听与拒接",
                isMultiLabel = true
            ),
            DomainItem(
                id = "query",
                name = "通用问答",
                description = "实时天气、时间日期、百科问答查询",
                isMultiLabel = true
            ),
            DomainItem(
                id = "other",
                name = "其他兜底",
                description = "无法分类或超出车控范围的开放域输入",
                isMultiLabel = false
            )
        )
    }
}
