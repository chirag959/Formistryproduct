package com.hypemarketer.callvault.data.repository

import com.hypemarketer.callvault.data.db.RecordingDao
import com.hypemarketer.callvault.data.db.RecordingEntity
import com.hypemarketer.callvault.data.db.TranscriptStatus
import com.hypemarketer.callvault.data.db.UploadStatus
import kotlinx.coroutines.flow.Flow

class RecordingRepository(private val dao: RecordingDao) {

    fun observeAll(): Flow<List<RecordingEntity>> = dao.observeAll()

    fun search(query: String): Flow<List<RecordingEntity>> = dao.search(query.trim())

    suspend fun get(id: Long): RecordingEntity? = dao.getById(id)

    suspend fun insert(recording: RecordingEntity): Long = dao.insert(recording)

    suspend fun markUploadStatus(id: Long, status: UploadStatus, driveFileId: String? = null) {
        val existing = dao.getById(id) ?: return
        dao.update(existing.copy(uploadStatus = status, driveFileId = driveFileId ?: existing.driveFileId))
    }

    suspend fun saveTranscript(id: Long, text: String) {
        val existing = dao.getById(id) ?: return
        dao.update(existing.copy(transcript = text, transcriptStatus = TranscriptStatus.DONE))
    }

    suspend fun markTranscriptStatus(id: Long, status: TranscriptStatus) {
        val existing = dao.getById(id) ?: return
        dao.update(existing.copy(transcriptStatus = status))
    }

    suspend fun delete(id: Long) = dao.delete(id)

    suspend fun pendingUploads(): List<RecordingEntity> = dao.pendingUploads()
    suspend fun pendingTranscriptions(): List<RecordingEntity> = dao.pendingTranscriptions()
}
