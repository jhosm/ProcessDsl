using ProcessDsl.Orchestration.Models;

namespace ProcessDsl.Orchestration;

/// <summary>
/// Interface for Camunda Zeebe REST API client
/// </summary>
public interface ICamundaClient
{
    /// <summary>
    /// Creates a new process instance
    /// </summary>
    /// <param name="processDefinitionKey">The BPMN process ID (e.g., "process-entity-demo")</param>
    /// <param name="request">Process start request with variables</param>
    /// <param name="cancellationToken">Cancellation token</param>
    /// <returns>Created process instance</returns>
    Task<ProcessInstance> CreateProcessInstanceAsync(
        string processDefinitionKey,
        StartProcessRequest request,
        CancellationToken cancellationToken = default);

    /// <summary>
    /// Creates a new process instance with a single entity variable
    /// </summary>
    /// <param name="processDefinitionKey">The BPMN process ID</param>
    /// <param name="entityData">Entity data to pass as "entityData" variable</param>
    /// <param name="cancellationToken">Cancellation token</param>
    /// <returns>Created process instance</returns>
    Task<ProcessInstance> CreateProcessInstanceWithEntityAsync(
        string processDefinitionKey,
        object entityData,
        CancellationToken cancellationToken = default);
}
