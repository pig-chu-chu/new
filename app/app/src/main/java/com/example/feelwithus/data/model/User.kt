package com.example.feelwithus.data.model

import android.app.Application
import android.os.Parcelable
import kotlinx.parcelize.Parcelize

@Parcelize
data class User(
    val username: String = ""    // 只帶帳號名稱等基本資訊
) : Parcelable

