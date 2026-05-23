package com.hypemarketer.callvault.data.db

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import kotlinx.coroutines.flow.Flow

@Dao
interface RecordingDao {

    @Query("SELECT * FROM recordings ORDER BY startedAt DESC")
    fun observeAll(): Flow<List<RecordingEntity>>

    @Query(
        """
        SELECT * FROM recordings
        WHERE contactName LIKE '%' || :q || '%'
           OR phoneNumber LIKE '%' || :q || '%'
           OR transcript LIKE '%' || :q || '%'
        ORDER BY startedAt DESC
        """,
    )
    fun search(q: String): Flow<List<RecordingEntity>>

    @Query("SELECT * FROM recordings WHERE id = :id")
    suspend fun getById(id: Long): RecordingEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(recording: RecordingEntity): Long

    @Update
    suspend fun update(recording: RecordingEntity)

    @Query("DELETE FROM recordings WHERE id = :id")
    suspend fun delete(id: Long)

    @Query("SELECT * FROM recordings WHERE uploadStatus IN ('PENDING', 'FAILED')")
    suspend fun pendingUploads(): List<RecordingEntity>

    @Query("SELECT * FROM recordings WHERE transcriptStatus = 'PENDING' AND uploadStatus = 'UPLOADED'")
    suspend fun pendingTranscriptions(): List<RecordingEntity>
}
