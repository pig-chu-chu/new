package com.example.feelwithus.data.model

data class LoginResponse(
    val success: Int,
    val message: String,
    val user: User?
)