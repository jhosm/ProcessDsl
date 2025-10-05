using ProcessDsl.Orchestration.Models;

namespace ProcessDsl.Orchestration;

/// <summary>
/// High-level orchestration interface for ProcessDsl workflows
/// </summary>
public interface IProcessOrchestrator
{
    /// <summary>
    /// Starts a process instance for an entity
    /// </summary>
    /// <param name="processId">The BPMN process ID from .bpm file</param>
    /// <param name="entityData">Entity data to process</param>
    /// <param name="cancellationToken">Cancellation token</param>
    /// <returns>Process instance information</returns>
    Task<ProcessInstance> StartProcessForEntityAsync(
        string processId,
        object entityData,
        CancellationToken cancellationToken = default);

    /// <summary>
    /// Starts a process instance with custom variables
    /// </summary>
    /// <param name="processId">The BPMN process ID from .bpm file</param>
    /// <param name="variables">Process variables</param>
    /// <param name="businessKey">Optional business key</param>
    /// <param name="cancellationToken">Cancellation token</param>
    /// <returns>Process instance information</returns>
    Task<ProcessInstance> StartProcessAsync(
        string processId,
        Dictionary<string, object> variables,
        string? businessKey = null,
        CancellationToken cancellationToken = default);
}
