package com.hypemarketer.callvault

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import androidx.work.Configuration
import com.hypemarketer.callvault.data.db.CallVaultDatabase
import com.hypemarketer.callvault.data.repository.RecordingRepository

class CallVaultApp : Application(), Configuration.Provider {

    val database: CallVaultDatabase by lazy { CallVaultDatabase.create(this) }
    val recordings: RecordingRepository by lazy { RecordingRepository(database.recordingDao()) }

    override fun onCreate() {
        super.onCreate()
        instance = this
        createNotificationChannels()
    }

    override val workManagerConfiguration: Configuration
        get() = Configuration.Builder()
            .setMinimumLoggingLevel(android.util.Log.INFO)
            .build()

    private fun createNotificationChannels() {
        val nm = getSystemService(NotificationManager::class.java)
        nm.createNotificationChannel(
            NotificationChannel(
                CHANNEL_RECORDING,
                getString(R.string.notification_channel_recording),
                NotificationManager.IMPORTANCE_LOW,
            ),
        )
        nm.createNotificationChannel(
            NotificationChannel(
                CHANNEL_SYNC,
                getString(R.string.notification_channel_sync),
                NotificationManager.IMPORTANCE_MIN,
            ),
        )
    }

    companion object {
        const val CHANNEL_RECORDING = "callvault.recording"
        const val CHANNEL_SYNC = "callvault.sync"

        private lateinit var instance: CallVaultApp
        fun get(): CallVaultApp = instance
    }
}
