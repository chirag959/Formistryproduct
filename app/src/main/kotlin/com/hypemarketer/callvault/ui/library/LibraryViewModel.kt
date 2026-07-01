package com.hypemarketer.callvault.ui.library

import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.hypemarketer.callvault.CallVaultApp
import com.hypemarketer.callvault.data.db.CallSource
import com.hypemarketer.callvault.data.db.RecordingEntity
import com.hypemarketer.callvault.data.db.TranscriptStatus
import com.hypemarketer.callvault.data.db.UploadStatus
import com.hypemarketer.callvault.recording.AudioRecorder
import com.hypemarketer.callvault.recording.CallRecordingService
import com.hypemarketer.callvault.transcription.TranscriptionQueue
import com.hypemarketer.callvault.util.AudioFileNamer
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class LibraryViewModel : ViewModel() {

    private val app = CallVaultApp.get()
    private val repo = app.recordings

    val query = MutableStateFlow("")
    val testRecording = MutableStateFlow<TestRecordingState>(TestRecordingState.Idle)

    @OptIn(ExperimentalCoroutinesApi::class)
    val recordings: StateFlow<List<RecordingEntity>> = query
        .flatMapLatest { q ->
            if (q.isBlank()) repo.observeAll() else repo.search(q)
        }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    fun setQuery(q: String) { query.value = q }

    fun delete(id: Long) {
        viewModelScope.launch { repo.delete(id) }
    }

    fun retryTranscription(id: Long) {
        TranscriptionQueue.enqueue(app, id)
    }

    /**
     * Records 10s from MIC while the Library screen is foreground, saves it, and enqueues
     * transcription. Bypasses the phone-call service — for smoke-testing the mic → save →
     * Gemini pipeline on a device without needing to make a real call.
     */
    fun startTestRecording(context: Context, seconds: Int = 10) {
        if (testRecording.value != TestRecordingState.Idle) return
        viewModelScope.launch {
            testRecording.value = TestRecordingState.Recording(seconds)
            val started = System.currentTimeMillis()
            val recorder = AudioRecorder(context)
            val dir = CallRecordingService.recordingsDir(context)
            val baseName = AudioFileNamer.fileBaseName("Test", started)
            val file = withContext(Dispatchers.IO) {
                runCatching { recorder.start(dir, baseName) }.getOrNull()
            }
            if (file == null) {
                testRecording.value = TestRecordingState.Error("Could not start MediaRecorder")
                return@launch
            }
            delay(seconds * 1000L)
            withContext(Dispatchers.IO) { recorder.stop() }
            val duration = ((System.currentTimeMillis() - started) / 1000).toInt()

            val id = repo.insert(
                RecordingEntity(
                    contactName = "Test recording",
                    phoneNumber = null,
                    source = CallSource.PHONE_OUTGOING,
                    startedAt = started,
                    durationSec = duration,
                    localPath = file.absolutePath,
                    driveFileId = null,
                    transcript = null,
                    uploadStatus = UploadStatus.PENDING,
                    transcriptStatus = TranscriptStatus.PENDING,
                ),
            )
            TranscriptionQueue.enqueue(context, id)
            testRecording.value = TestRecordingState.Idle
        }
    }
}

sealed interface TestRecordingState {
    data object Idle : TestRecordingState
    data class Recording(val seconds: Int) : TestRecordingState
    data class Error(val message: String) : TestRecordingState
}
