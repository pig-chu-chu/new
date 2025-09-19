package com.example.feelwithus.data.network

import com.example.feelwithus.data.model.LoginResponse
import com.example.feelwithus.data.model.Match
import com.example.feelwithus.data.model.RegisterResponse
import com.google.gson.annotations.SerializedName
import okhttp3.ResponseBody
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.FormUrlEncoded
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Query
import retrofit2.http.Streaming
import retrofit2.http.Field

data class StartResponse(val message: String)
data class RoiBody(val roi: List<Int>)
data class JerseyBody(
    @SerializedName("jersey")
    val jersey: String
)

data class AnalysisStatusResponse(
    val status: String
)

// 通用回傳結果 (成功/失敗訊息)
data class GenericResponse(
    val success: Boolean,
    val status: String? = null,
    val message: String? = null
)

// 傳送影片名稱
data class VideoNameRequest(
    val videoName: String
)


interface RetrofitServiceA {
    //  163.13.201.90 伺服器
    @FormUrlEncoded
    @POST("app/login.php")
    suspend fun login(
        @Field("username") username: String,
        @Field("password") password: String
    ): Response<LoginResponse>

    @FormUrlEncoded
    @POST("app/register.php")
    suspend fun register(
        @Field("username") username: String,
        @Field("password") password: String,
    ): Response<RegisterResponse>

    @GET("3d_video/video_list.php")
    suspend fun get3DvideoList(): Response<List<Match>>

    @GET("video/video_list.php")
    suspend fun getMatchFootageList(): Response<List<Match>>
}

interface RetrofitServiceB {
    //  163.13.202.124  辨識Ai
    @POST("/start")
    suspend fun startAnalysis(): Response<StartResponse>

    @GET("/get_first_frame")
    @Streaming
    suspend fun getFirstFrame(): Response<ResponseBody>

    @POST("/submit_roi")
    suspend fun submitRoi(@Body body: RoiBody): Response<RoiResponse>

    @POST("/submit_jersey")
    suspend fun submitJersey(@Body body: JerseyBody): Response<Unit>

    @GET("/analysis_status")
    suspend fun analysisStatus(): Response<AnalysisStatusResponse>

    @POST("/run_analysis")
    suspend fun runAnalysis(): Response<Unit>

}

interface RetrofitServiceC {
    //  手套
    /**
     * 傳送影片名稱給 IoT ，使伺服器尋找並載入對應的動作指令資料表
     * POST db_start
     */
    @POST("api/db_start")
    suspend fun dbStart(@Body body: VideoNameRequest): Response<GenericResponse>

    /**
     * 執行時的 on/off 控制（保持伺服器接收）
     * POST Switch（boolean 值）
     */
    @POST("api/switch")
    suspend fun switch(@Body enabled: Boolean): Response<GenericResponse>

    /**
     * 從伺服器取得是否已有動作指令資料表的狀態
     * GET status（boolean）
     */
    @GET("api/status")
    suspend fun status(): Response<Boolean>

    /**
     * 使用者主動停止全部動作並停止接收伺服器
     * POST db_stop
     */
    @POST("api/db_stop")
    suspend fun dbStop(@Body stopCommand: String): Response<GenericResponse>

    /**
     * 影片被動結束，停止接收伺服器動作指令
     * GET end
     */
    @GET("api/end")
    suspend fun end(): Response<GenericResponse>
}

interface RetrofitServiceD {
    //  氣味
    @POST("api/db_start")
    suspend fun dbStart(@Body body: VideoNameRequest): Response<GenericResponse>

    @POST("api/switch")
    suspend fun switch(@Body enabled: Boolean): Response<GenericResponse>

    @GET("api/status")
    suspend fun status(): Response<Boolean>

    @POST("api/db_stop")
    suspend fun dbStop(@Body stopCommand: String): Response<GenericResponse>

    @GET("api/end")
    suspend fun end(): Response<GenericResponse>
}

interface RetrofitServiceE {
    // 切換影片
    @POST("api/video/basketball_1")
    suspend fun switchToBasketball1(): Response<Unit>

    @POST("api/video/basketball_3")
    suspend fun switchToBasketball3(): Response<Unit>

    @POST("api/video/volleyball_1")
    suspend fun switchToVolleyball1(): Response<Unit>

    @POST("api/device/on")
    suspend fun playVideo(): Response<Unit>

    @POST("api/device/off")
    suspend fun pauseVideo(): Response<Unit>
}