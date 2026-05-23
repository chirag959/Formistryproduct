package com.hypemarketer.callvault.transcription

import android.content.Context
import androidx.work.BackoffPolicy
import androidx.work.Constraints
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.workDataOf
import java.util.concurrent.TimeUnit

object TranscriptionQueue {
    const val KEY_RECORDING_ID = "recordingId"

    fun enqueue(context: Context, recordingId: Long) {
        val req = OneTimeWorkRequestBuilder<TranscriptionWorker>()
            .setInputData(workDataOf(KEY_RECORDING_ID to recordingId))
            .setConstraints(
                Constraints.Builder()
                    .setRequiredNetworkType(NetworkType.CONNECTED)
                    .build(),
            )
            .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 30, TimeUnit.SECONDS)
            .addTag(TAG)
            .build()
        WorkManager.getInstance(context).enqueue(req)
    }

    const val TAG = "callvault.transcription"
}
