using UnityEngine;

public class CameraFollow : MonoBehaviour
{
    [Header("要跟隨的目標，拖你的球員物件")]
    public Transform target;

    [Header("鏡頭相對角色的距離設定")]
    public float distance = 6f;   // 與角色距離
    public float height = 2f;     // 高度

    [Header("角度調整 (Pitch, Yaw, Roll)")]
    [Range(-80, 80)] public float pitch = 20f;   // 上下俯仰角
    [Range(-180, 180)] public float yaw = 0f;    // 左右水平角
    [Range(-45, 45)] public float roll = 0f;     // 左右傾斜角

    [Header("追蹤平滑參數，0 = 立即跳到目標位置；越大越平滑")]
    public float smoothSpeed = 5f;

    void LateUpdate()
    {
        if (target == null) return;

        // 1. 以角色為中心，計算旋轉角度
        Quaternion rotation = Quaternion.Euler(pitch, yaw, roll);

        // 2. 根據旋轉角度和距離，算出鏡頭位置
        Vector3 desiredPos = target.position 
                           + rotation * new Vector3(0f, height, -distance);

        // 3. 平滑移動到理想位置
        Vector3 smoothedPos = Vector3.Lerp(transform.position, desiredPos, smoothSpeed * Time.deltaTime);
        transform.position = smoothedPos;

        // 4. 讓鏡頭面向角色
        transform.LookAt(target.position + Vector3.up * (height * 0.5f));
    }
}
