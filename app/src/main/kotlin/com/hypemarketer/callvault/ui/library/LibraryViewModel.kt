package com.hypemarketer.callvault.ui.library

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.hypemarketer.callvault.CallVaultApp
import com.hypemarketer.callvault.data.db.RecordingEntity
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

class LibraryViewModel : ViewModel() {

    private val repo = CallVaultApp.get().recordings

    val query = MutableStateFlow("")

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
}
