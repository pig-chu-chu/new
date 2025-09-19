package com.example.feelwithus.data.model

import com.google.gson.annotations.SerializedName

data class Match(
    @SerializedName("id") val id: String,
    @SerializedName("file_name") val fileName: String,
    @SerializedName("file_path") val filePath: String,
    @SerializedName("upload_time") val uploadTime: String,
    @SerializedName("description") val description: String
)