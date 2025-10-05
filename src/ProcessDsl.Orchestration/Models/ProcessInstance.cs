namespace ProcessDsl.Orchestration.Models;

/// <summary>
/// Represents a Camunda process instance
/// </summary>
public class ProcessInstance
{
    /// <summary>
    /// Unique process instance key
    /// </summary>
    public long ProcessInstanceKey { get; set; }

    /// <summary>
    /// Process definition key
    /// </summary>
    public long ProcessDefinitionKey { get; set; }

    /// <summary>
    /// BPMN process ID
    /// </summary>
    public string? BpmnProcessId { get; set; }

    /// <summary>
    /// Process version
    /// </summary>
    public int Version { get; set; }

    /// <summary>
    /// Tenant ID (for multi-tenancy)
    /// </summary>
    public string? TenantId { get; set; }
}
