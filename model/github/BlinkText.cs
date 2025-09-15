using UnityEngine;
using TMPro;

[RequireComponent(typeof(TextMeshProUGUI))]
public class BlinkText : MonoBehaviour
{
    [Header("Target")]
    public TextMeshProUGUI label;

    [Header("Blink Settings")]
    [Tooltip("每秒閃爍次數")]
    public float blinkSpeed = 2f;
    [Tooltip("最小透明度 (0 = 全透明, 1 = 完全不透明)")]
    [Range(0f, 1f)] public float minAlpha = 0f;
    [Tooltip("最大透明度 (0 = 全透明, 1 = 完全不透明)")]
    [Range(0f, 1f)] public float maxAlpha = 1f;

    [Header("Control")]
    public bool isBlinking = true; // 可隨時啟動/停止

    Color originalColor;

    void Awake()
    {
        if (label == null)
            label = GetComponent<TextMeshProUGUI>();

        originalColor = label.color;
    }

    void OnEnable()
    {
        // 確保恢復初始顏色
        if (label != null)
            label.color = originalColor;
    }

    void Update()
    {
        if (!isBlinking || label == null) return;

        // Sin 波在 -1 ~ 1 之間 → Abs → 0 ~ 1
        float t = Mathf.Abs(Mathf.Sin(Time.time * blinkSpeed * Mathf.PI));
        // 插值到 min/max 範圍
        float alpha = Mathf.Lerp(minAlpha, maxAlpha, t);

        Color c = originalColor;
        c.a = alpha;
        label.color = c;
    }

    // 外部呼叫：開始閃爍
    public void StartBlink()
    {
        isBlinking = true;
    }

    // 外部呼叫：停止閃爍並回復原始顏色
    public void StopBlink()
    {
        isBlinking = false;
        if (label != null) label.color = originalColor;
    }
}
