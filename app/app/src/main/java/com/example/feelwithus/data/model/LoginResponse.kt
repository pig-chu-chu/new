package com.example.feelwithus.data.model

data class LoginResponse(
    val success: Int,
    val message: String,
    val user: User? // User 中只含基本欄位即可
)