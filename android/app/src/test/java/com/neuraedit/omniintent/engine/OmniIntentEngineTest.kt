package com.neuraedit.omniintent.engine

import com.neuraedit.omniintent.model.DomainItem
import com.neuraedit.omniintent.model.IntentVerdict
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

class OmniIntentEngineTest {

    private val defaultDomains = DomainItem.defaultDomains()

    @Test
    fun testMultiIntentDecision_MusicAndClimate() = runBlocking {
        val query = "周杰伦的稻香，顺便把空调开到24度"
        val result = OmniIntentEngine.decide(
            query = query,
            isCloudMode = false,
            cloudEndpoint = "",
            domains = defaultDomains
        )

        // Verify multi-label detection
        val activeIntents = result.intents.filter { it.verdict == IntentVerdict.ACTIVE }.map { it.domainId }
        assertTrue("Must detect music intent", activeIntents.contains("music"))
        assertTrue("Must detect climate intent", activeIntents.contains("climate"))

        // Verify slots
        assertEquals("周杰伦 / Jay Chou", result.slots.musicArtist)
        assertEquals("稻香 / Fragrance of Rice", result.slots.musicSong)
        assertEquals("24 ℃ / 24 °C", result.slots.climateTemp)
    }

    @Test
    fun testNavigationWithNegation() = runBlocking {
        val query = "导航去虹桥机场，避开拥堵但不要走高速"
        val result = OmniIntentEngine.decide(
            query = query,
            isCloudMode = false,
            cloudEndpoint = "",
            domains = defaultDomains
        )

        val activeIntents = result.intents.filter { it.verdict == IntentVerdict.ACTIVE }.map { it.domainId }
        assertTrue("Must detect navigation intent", activeIntents.contains("navigation"))

        // Verify slot and negation
        assertEquals("虹桥国际机场 / Hongqiao Airport", result.slots.navDestination)
        assertTrue("Must detect negation constraints", result.slots.negations.isNotEmpty())
        assertTrue(result.slots.negations.any { it.contains("不要走高速") || it.contains("避开拥堵") })
    }

    @Test
    fun testWindowAndSeatSlots() = runBlocking {
        val query1 = "把副驾车窗降下一半"
        val slots1 = OmniIntentEngine.extractLocalSlots(query1)
        assertEquals("副驾车窗 / Passenger Window", slots1.windowZone)
        assertEquals("降下一半 (50%) / Roll Down 50%", slots1.windowAction)

        val query2 = "打开主驾座椅加热"
        val slots2 = OmniIntentEngine.extractLocalSlots(query2)
        assertEquals("主驾座椅 / Driver Seat", slots2.seatZone)
        assertEquals("座椅加热 / Seat Heating", slots2.seatAction)
    }

    @Test
    fun testSongTitleSuffixCleaning_SimplifiedAndTraditional() = runBlocking {
        // Test Simplified Chinese input with "这首歌"
        val querySimp = "要听八三夭的外婆的告别式这首歌"
        val slotsSimp = OmniIntentEngine.extractLocalSlots(querySimp)
        assertEquals("八三夭 / 831", slotsSimp.musicArtist)
        assertEquals("外婆的告别式 / Grandma's Farewell", slotsSimp.musicSong)

        // Test Traditional Chinese input with "這首歌"
        val queryTrad = "要聽八三夭的外婆的告別式這首歌"
        val slotsTrad = OmniIntentEngine.extractLocalSlots(queryTrad)
        assertEquals("八三夭 / 831", slotsTrad.musicArtist)
        assertEquals("外婆的告别式 / Grandma's Farewell", slotsTrad.musicSong)
    }

    @Test
    fun testTraditionalChineseNegationAndGating() = runBlocking {
        val query = "關閉空調，但是不要關座椅加熱"
        val result = OmniIntentEngine.decide(
            query = query,
            isCloudMode = false,
            cloudEndpoint = "",
            domains = defaultDomains
        )

        val climateIntent = result.intents.find { it.domainId == "climate" }
        assertNotNull("Climate intent must exist", climateIntent)
        assertEquals("turn_off", climateIntent?.actionType)

        val seatIntent = result.intents.find { it.domainId == "seat" }
        assertNotNull("Seat intent must exist", seatIntent)
        assertEquals("exclude", seatIntent?.actionType)
        assertEquals(IntentVerdict.EXCLUDED, seatIntent?.verdict)
    }

    @Test
    fun testTelemetryMetricsCalculated() = runBlocking {
        val query = "把温度调低两度，不要开外循环"
        val result = OmniIntentEngine.decide(
            query = query,
            isCloudMode = false,
            cloudEndpoint = "",
            domains = defaultDomains
        )

        assertTrue(result.wallClockMs > 0)
        assertTrue(result.modelComputeMs > 0)
        assertTrue(result.tokenCount > 0)
        assertNotNull(result.engineName)
    }
}
