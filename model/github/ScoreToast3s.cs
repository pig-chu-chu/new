using System.Collections;
using UnityEngine;
using TMPro;

[RequireComponent(typeof(CanvasGroup))]
public class ScoreToast3s : MonoBehaviour
{
    [Header("Refs")]
    public TextMeshProUGUI label;   // 拖入你的 TMP 文字
    private CanvasGroup group;

    [Header("Timing")]
    public float visibleSeconds = 2f;   // 完整顯示時間
    public float fadeSeconds = 1f;      // 淡出時間 (總長 = visible + fade)

    [Header("Style")]
    public bool popOnShow = true;       // 顯示時小彈跳
    public AnimationCurve popScale = AnimationCurve.EaseInOut(0, 1f, 0.12f, 1.08f);
    public float popDuration = 0.18f;

    [Header("Behavior")]
    public bool deactivateOnHide = false;  // 結束時是否關閉物件（避免和 Activation Track 打架，預設不關）
    public bool resetScaleOnShow = true;   // 每次顯示前把 Scale 重設為 1

    Coroutine co;

    void Awake()
    {
        group = GetComponent<CanvasGroup>();
        if (!label) label = GetComponentInChildren<TextMeshProUGUI>();
        group.alpha = 0f;
        transform.localScale = Vector3.one;
    }

    /// <summary>
    /// Timeline 在進球那格呼叫：顯示文字 visibleSeconds 秒，接著 fadeSeconds 秒淡出。
    /// </summary>
    public void Show3s(string text)
    {
        if (label) label.text = text;

        if (co != null) StopCoroutine(co);
        if (resetScaleOnShow) transform.localScale = Vector3.one;

        gameObject.SetActive(true);
        group.alpha = 1f;

        if (popOnShow) StartCoroutine(PopOnceRealtime());
        co = StartCoroutine(PlayRoutineRealtime());
    }

    IEnumerator PlayRoutineRealtime()
    {
        // 1) 保持顯示（不受 timeScale 影響）
        if (visibleSeconds > 0f)
            yield return new WaitForSecondsRealtime(visibleSeconds);

        // 2) 淡出（使用 unscaledDeltaTime）
        float t = 0f;
        float start = group.alpha;
        while (t < fadeSeconds)
        {
            t += Time.unscaledDeltaTime;
            float k = Mathf.Clamp01(fadeSeconds > 0f ? t / fadeSeconds : 1f);
            group.alpha = Mathf.Lerp(start, 0f, k);
            yield return null;
        }

        group.alpha = 0f;
        if (deactivateOnHide) gameObject.SetActive(false);
        co = null;
    }

    IEnumerator PopOnceRealtime()
    {
        float t = 0f;
        Vector3 baseScale = Vector3.one;
        while (t < popDuration)
        {
            t += Time.unscaledDeltaTime;
            float k = Mathf.Clamp01(popDuration > 0f ? t / popDuration : 1f);
            float s = popScale.Evaluate(k);
            transform.localScale = baseScale * s;
            yield return null;
        }
        transform.localScale = baseScale;
    }

    // ───── 方便在 Timeline/Signal 用的小工具方法（可選）─────
    public void SetText(string s)
    {
        if (label) label.text = s;
    }
    public void SetFontSize(float size)
    {
        if (!label) return;
        label.enableAutoSizing = false;
        label.fontSize = size;
        label.ForceMeshUpdate();
    }
    public void UseAutoSize(float min, float max)
    {
        if (!label) return;
        label.enableAutoSizing = true;
        label.fontSizeMin = min;
        label.fontSizeMax = max;
        label.ForceMeshUpdate();
    }
    public void HideNow()
    {
        if (co != null) StopCoroutine(co);
        group.alpha = 0f;
        if (deactivateOnHide) gameObject.SetActive(false);
        co = null;
    }

    // 右鍵元件選單：Play 模式快速測試
    [ContextMenu("TEST: Show Now")]
    void TestShowNow() { Show3s("TEST 12 : 10"); }
}
