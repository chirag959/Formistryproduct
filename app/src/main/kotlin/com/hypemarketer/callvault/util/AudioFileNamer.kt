package com.hypemarketer.callvault.util

import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

object AudioFileNamer {
    private val FORMAT = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US)

    fun fileBaseName(contactName: String, startedAt: Long): String {
        val safe = contactName.replace(Regex("[^A-Za-z0-9_-]"), "_").take(40)
        return "${safe}_${FORMAT.format(Date(startedAt))}"
    }
}
