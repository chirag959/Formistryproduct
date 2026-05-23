package com.hypemarketer.callvault.data.db

import androidx.room.Entity
import androidx.room.PrimaryKey

enum class CallSource { PHONE_INCOMING, PHONE_OUTGOING, WHATSAPP }

enum class UploadStatus { PENDING, UPLOADING, UPLOADED, FAILED }

enum class TranscriptStatus { PENDING, PROCESSING, DONE, FAILED }

@Entity(tableName = "recordings")
data class RecordingEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val contactName: String,
    val phoneNumber: String?,
    val source: CallSource,
    val startedAt: Long,
    val durationSec: Int,
    val localPath: String?,
    val driveFileId: String?,
    val transcript: String?,
    val uploadStatus: UploadStatus,
    val transcriptStatus: TranscriptStatus,
)
