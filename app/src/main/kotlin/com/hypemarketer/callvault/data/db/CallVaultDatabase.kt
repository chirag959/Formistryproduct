package com.hypemarketer.callvault.data.db

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.TypeConverter
import androidx.room.TypeConverters

class Converters {
    @TypeConverter fun fromSource(v: CallSource): String = v.name
    @TypeConverter fun toSource(v: String): CallSource = CallSource.valueOf(v)

    @TypeConverter fun fromUpload(v: UploadStatus): String = v.name
    @TypeConverter fun toUpload(v: String): UploadStatus = UploadStatus.valueOf(v)

    @TypeConverter fun fromTranscript(v: TranscriptStatus): String = v.name
    @TypeConverter fun toTranscript(v: String): TranscriptStatus = TranscriptStatus.valueOf(v)
}

@Database(entities = [RecordingEntity::class], version = 1, exportSchema = true)
@TypeConverters(Converters::class)
abstract class CallVaultDatabase : RoomDatabase() {
    abstract fun recordingDao(): RecordingDao

    companion object {
        fun create(context: Context): CallVaultDatabase =
            Room.databaseBuilder(context, CallVaultDatabase::class.java, "callvault.db").build()
    }
}
