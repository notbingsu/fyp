using UnityEngine;
using TMPro;
using UnityEngine.SceneManagement;

public class TrainingManager : MonoBehaviour
{
    public static TrainingManager Instance;

    [Header("UI Display")]
    public TextMeshProUGUI statsText;
    public GameObject successTabletObject;

    [Header("Haptic Device")]
    [Tooltip("Drag your HapticPlugin GameObject here. Force scripts are found on it automatically.")]
    public HapticPlugin hapticPlugin;

    // --- Auto-found from hapticPlugin GameObject ---
    private ExperimentRecorder recorder;
    private WaypointForceGuidance waypointGuidance;
    private ExpertForceControl expertControl;

    // --- Set at runtime by ExperimentSettingsUI ---
    [HideInInspector] public string participantID = "P001";
    [HideInInspector] public ExperimentCondition condition = ExperimentCondition.Control;

    // --- Set per scenario by ScenarioStartController ---
    [HideInInspector] public string currentScenarioName = "unknown";

    private float startTime;
    private int hitCount = 0;
    private int clickCount = 0;
    private bool isTrainingActive = false;

    public bool IsTrainingActive => isTrainingActive;

    public enum ExperimentCondition
    {
        Control,
        WaypointGuidance,
        ExpertControlled
    }

    void Awake()
    {
        Instance = this;
        if (successTabletObject != null) successTabletObject.SetActive(false);

        // Find recorder (usually on same GameObject as TrainingManager)
        recorder = GetComponent<ExperimentRecorder>();
        if (recorder == null) recorder = FindObjectOfType<ExperimentRecorder>();

        // Find force scripts on the HapticPlugin GameObject
        FindForceScripts();
    }

    private void FindForceScripts()
    {
        if (hapticPlugin == null)
            hapticPlugin = FindObjectOfType<HapticPlugin>();

        if (hapticPlugin != null)
        {
            waypointGuidance = hapticPlugin.GetComponent<WaypointForceGuidance>();
            expertControl = hapticPlugin.GetComponent<ExpertForceControl>();

            Debug.Log($"[TrainingManager] Found on HapticPlugin — " +
                      $"Waypoint: {(waypointGuidance != null ? "YES" : "NO")}, " +
                      $"Expert: {(expertControl != null ? "YES" : "NO")}");
        }
        else
        {
            Debug.LogWarning("[TrainingManager] HapticPlugin not found!");
        }
    }

    public void SetScenario(string scenarioName)
    {
        currentScenarioName = scenarioName;
    }

    public void StartScenario()
    {
        Debug.Log($"Scenario Started! [{participantID}] [{condition}] [{currentScenarioName}]");
        hitCount = 0;
        clickCount = 0;
        startTime = Time.time;
        isTrainingActive = true;

        if (recorder != null)
            recorder.StartRecording(participantID, currentScenarioName, condition.ToString());

        bool hapticEnabled = condition != ExperimentCondition.Control;
        HapticServerClient.Instance?.SendStart(participantID, currentScenarioName, hapticEnabled);

        StartForceGuidance();
    }

    public void AddHit(string objectName = "")
    {
        if (isTrainingActive)
        {
            hitCount++;
            Debug.Log("Hit Registered! Total: " + hitCount);

            if (recorder != null)
                recorder.MarkCollision(objectName);
        }
    }

    public void AddClick()
    {
        if (isTrainingActive)
        {
            clickCount++;
            Debug.Log("Click Registered! Total: " + clickCount);

            if (recorder != null)
                recorder.MarkClick();
        }
    }

    public void CompleteScenario()
    {
        if (!isTrainingActive) return;
        isTrainingActive = false;

        float duration = Time.time - startTime;
        string formattedTime = FormatTime(duration);
        int wastedClicks = Mathf.Max(0, clickCount - 1);

        StopForceGuidance();
        HapticServerClient.Instance?.SendStop();

        if (recorder != null)
            recorder.StopRecording(duration, hitCount, clickCount);

        if (successTabletObject != null) successTabletObject.SetActive(true);
        if (statsText != null)
        {
            statsText.text = $"<b>SCENARIO COMPLETE</b>\n\n" +
                             $"Time: {formattedTime}\n" +
                             $"Collisions: <color=red>{hitCount}</color>\n" +
                             $"Wasted Clicks: <color=red>{wastedClicks}</color>";
        }
    }

    private string FormatTime(float time)
    {
        int seconds = (int)time;
        int milliseconds = (int)((time - seconds) * 1000);
        return string.Format("{0}.{1:000}s", seconds, milliseconds);
    }

    public void RestartGame()
    {
        SceneManager.LoadScene(SceneManager.GetActiveScene().name);
    }

    // ==================== FORCE FEEDBACK ====================

    private void StartForceGuidance()
    {
        // Only apply force feedback during training, not testing
        if (currentScenarioName != "Training") return;
        
        // Re-find if not yet found (e.g. scripts added after Awake)
        if (waypointGuidance == null || expertControl == null)
            FindForceScripts();

        switch (condition)
        {
            case ExperimentCondition.Control:
                Debug.Log("[TrainingManager] Control condition — no force feedback");
                break;

            case ExperimentCondition.WaypointGuidance:
                if (waypointGuidance != null)
                {
                    if (waypointGuidance.LoadWaypoints(currentScenarioName))
                    {
                        waypointGuidance.StartGuidance();
                    }
                    else
                    {
                        Debug.LogWarning($"[TrainingManager] Failed to load waypoints for '{currentScenarioName}'");
                    }
                }
                else
                {
                    Debug.LogWarning("[TrainingManager] WaypointForceGuidance not found on HapticPlugin!");
                }
                break;

            case ExperimentCondition.ExpertControlled:
                if (expertControl != null)
                {
                    expertControl.StartControl();
                }
                else
                {
                    Debug.LogWarning("[TrainingManager] ExpertForceControl not found on HapticPlugin!");
                }
                break;
        }
    }

    private void StopForceGuidance()
    {
        if (waypointGuidance != null && waypointGuidance.enabled)
            waypointGuidance.StopGuidance();

        if (expertControl != null && expertControl.enabled)
            expertControl.StopControl();
    }
}