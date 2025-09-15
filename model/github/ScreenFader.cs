using UnityEngine;
using UnityEngine.UI;
using System.Collections;

[RequireComponent(typeof(Image))]
public class ScreenFader : MonoBehaviour
{
    [Header("Refs")]
    public Image blackScreen;            // 建議掛在同一個物件上

    [Header("Durations")]
    [Tooltip("淡入/淡出所需秒數")]
    public float fadeDuration = 0.3f;
    [Tooltip("全黑停留秒數")]
    public float holdTime = 1f;

    [Header("Init")]
    [Tooltip("載入時是否自動把黑幕設為透明")]
    public bool startHidden = true;

    Coroutine co;

    void Awake()
    {
        if (!blackScreen) blackScreen = GetComponent<Image>();
        if (startHidden && blackScreen)
        {
            var c = blackScreen.color; c.a = 0f;
            blackScreen.color = c;
        }
    }

    // —— 主要對外 API ——
    public void FlashBlack() => Flash(holdTime, fadeDuration);

    /// <summary>自訂停留與淡入/淡出速度</summary>
    public void Flash(float holdSeconds, float fadeSeconds)
    {
        if (!blackScreen) return;
        fadeDuration = Mathf.Max(0f, fadeSeconds);
        if (co != null) StopCoroutine(co);
        co = StartCoroutine(CoFlash(holdSeconds));
    }

    /// <summary>只淡入至全黑</summary>
    public void FadeIn()
    {
        if (!blackScreen) return;
        if (co != null) StopCoroutine(co);
        co = StartCoroutine(CoFade(0f, 1f, fadeDuration));
    }

    /// <summary>只從全黑淡出到透明</summary>
    public void FadeOut()
    {
        if (!blackScreen) return;
        if (co != null) StopCoroutine(co);
        co = StartCoroutine(CoFade(1f, 0f, fadeDuration));
    }

    // —— 內部協程 ——
    IEnumerator CoFlash(float holdSeconds)
    {
        Debug.Log("[Fader] FlashBlack received");
        yield return CoFade(0f, 1f, fadeDuration);               // 淡入黑
        if (holdSeconds > 0f) yield return new WaitForSeconds(holdSeconds);
        yield return CoFade(1f, 0f, fadeDuration);               // 淡出黑
        co = null;
    }

    IEnumerator CoFade(float from, float to, float duration)
    {
        float t = 0f;
        var c = blackScreen.color;
        while (t < duration)
        {
            t += Time.deltaTime;
            c.a = Mathf.Lerp(from, to, duration <= 0f ? 1f : t / duration);
            blackScreen.color = c;
            yield return null;
        }
        c.a = to;
        blackScreen.color = c;
    }
}
