namespace ProcessDsl.Orchestration.Models;

/// <summary>
/// Request model for starting a Camunda process instance
/// </summary>
public class StartProcessRequest
{
    /// <summary>
    /// Process variables as key-value pairs
    /// </summary>
    public Dictionary<string, object> Variables { get; set; } = new();

    /// <summary>
    /// Optional business key for the process instance
    /// </summary>
    public string? BusinessKey { get; set; }

    /// <summary>
    /// Tenant ID for multi-tenancy scenarios
    /// </summary>
    public string? TenantId { get; set; }
}
