using FluentAssertions;
using Microsoft.Extensions.Logging;
using Moq;
using ProcessDsl.Orchestration.Models;
using Xunit;

namespace ProcessDsl.Orchestration.Tests;

public class ProcessOrchestratorTests
{
    private readonly Mock<ICamundaClient> _camundaClientMock;
    private readonly Mock<ILogger<ProcessOrchestrator>> _loggerMock;
    private readonly ProcessOrchestrator _orchestrator;

    public ProcessOrchestratorTests()
    {
        _camundaClientMock = new Mock<ICamundaClient>();
        _loggerMock = new Mock<ILogger<ProcessOrchestrator>>();
        _orchestrator = new ProcessOrchestrator(_camundaClientMock.Object, _loggerMock.Object);
    }

    [Fact]
    public async Task StartProcessForEntityAsync_Success_ReturnsProcessInstance()
    {
        // Arrange
        var processId = "process-entity-demo";
        var entityData = new { Id = "cust-123", Name = "John Doe" };
        var expectedInstance = new ProcessInstance
        {
            ProcessInstanceKey = 12345,
            BpmnProcessId = processId,
            Version = 1
        };

        _camundaClientMock
            .Setup(x => x.CreateProcessInstanceWithEntityAsync(
                processId,
                entityData,
                It.IsAny<CancellationToken>()))
            .ReturnsAsync(expectedInstance);

        // Act
        var result = await _orchestrator.StartProcessForEntityAsync(processId, entityData);

        // Assert
        result.Should().NotBeNull();
        result.ProcessInstanceKey.Should().Be(12345);
        result.BpmnProcessId.Should().Be(processId);
        
        _camundaClientMock.Verify(
            x => x.CreateProcessInstanceWithEntityAsync(processId, entityData, It.IsAny<CancellationToken>()),
            Times.Once);
    }

    [Fact]
    public async Task StartProcessForEntityAsync_NullProcessId_ThrowsArgumentException()
    {
        // Arrange
        var entityData = new { Id = "123" };

        // Act & Assert
        await Assert.ThrowsAsync<ArgumentException>(
            () => _orchestrator.StartProcessForEntityAsync(null!, entityData));
    }

    [Fact]
    public async Task StartProcessForEntityAsync_EmptyProcessId_ThrowsArgumentException()
    {
        // Arrange
        var entityData = new { Id = "123" };

        // Act & Assert
        await Assert.ThrowsAsync<ArgumentException>(
            () => _orchestrator.StartProcessForEntityAsync("", entityData));
    }

    [Fact]
    public async Task StartProcessForEntityAsync_NullEntityData_ThrowsArgumentNullException()
    {
        // Act & Assert
        await Assert.ThrowsAsync<ArgumentNullException>(
            () => _orchestrator.StartProcessForEntityAsync("test-process", null!));
    }

    [Fact]
    public async Task StartProcessForEntityAsync_CamundaError_ThrowsAndLogs()
    {
        // Arrange
        var processId = "process-entity-demo";
        var entityData = new { Id = "123" };
        var exception = new HttpRequestException("Camunda service unavailable");

        _camundaClientMock
            .Setup(x => x.CreateProcessInstanceWithEntityAsync(
                It.IsAny<string>(),
                It.IsAny<object>(),
                It.IsAny<CancellationToken>()))
            .ThrowsAsync(exception);

        // Act & Assert
        await Assert.ThrowsAsync<HttpRequestException>(
            () => _orchestrator.StartProcessForEntityAsync(processId, entityData));

        // Verify error was logged
        _loggerMock.Verify(
            x => x.Log(
                LogLevel.Error,
                It.IsAny<EventId>(),
                It.Is<It.IsAnyType>((v, t) => true),
                It.IsAny<Exception>(),
                It.IsAny<Func<It.IsAnyType, Exception?, string>>()),
            Times.Once);
    }

    [Fact]
    public async Task StartProcessAsync_Success_ReturnsProcessInstance()
    {
        // Arrange
        var processId = "test-process";
        var variables = new Dictionary<string, object>
        {
            ["var1"] = "value1",
            ["var2"] = 42
        };
        var businessKey = "biz-key-123";

        var expectedInstance = new ProcessInstance
        {
            ProcessInstanceKey = 67890,
            BpmnProcessId = processId,
            Version = 2
        };

        _camundaClientMock
            .Setup(x => x.CreateProcessInstanceAsync(
                processId,
                It.Is<StartProcessRequest>(req =>
                    req.Variables == variables &&
                    req.BusinessKey == businessKey),
                It.IsAny<CancellationToken>()))
            .ReturnsAsync(expectedInstance);

        // Act
        var result = await _orchestrator.StartProcessAsync(processId, variables, businessKey);

        // Assert
        result.Should().NotBeNull();
        result.ProcessInstanceKey.Should().Be(67890);
        result.BpmnProcessId.Should().Be(processId);
        result.Version.Should().Be(2);
    }

    [Fact]
    public async Task StartProcessAsync_NullProcessId_ThrowsArgumentException()
    {
        // Arrange
        var variables = new Dictionary<string, object>();

        // Act & Assert
        await Assert.ThrowsAsync<ArgumentException>(
            () => _orchestrator.StartProcessAsync(null!, variables));
    }

    [Fact]
    public async Task StartProcessAsync_NullVariables_ThrowsArgumentNullException()
    {
        // Act & Assert
        await Assert.ThrowsAsync<ArgumentNullException>(
            () => _orchestrator.StartProcessAsync("test-process", null!));
    }

    [Fact]
    public async Task StartProcessAsync_WithoutBusinessKey_Success()
    {
        // Arrange
        var processId = "test-process";
        var variables = new Dictionary<string, object> { ["key"] = "value" };
        var expectedInstance = new ProcessInstance { ProcessInstanceKey = 111 };

        _camundaClientMock
            .Setup(x => x.CreateProcessInstanceAsync(
                It.IsAny<string>(),
                It.IsAny<StartProcessRequest>(),
                It.IsAny<CancellationToken>()))
            .ReturnsAsync(expectedInstance);

        // Act
        var result = await _orchestrator.StartProcessAsync(processId, variables);

        // Assert
        result.Should().NotBeNull();
        result.ProcessInstanceKey.Should().Be(111);
    }

    [Fact]
    public void Constructor_NullCamundaClient_ThrowsArgumentNullException()
    {
        // Act & Assert
        Assert.Throws<ArgumentNullException>(
            () => new ProcessOrchestrator(null!, _loggerMock.Object));
    }

    [Fact]
    public void Constructor_NullLogger_DoesNotThrow()
    {
        // Act & Assert
        var exception = Record.Exception(
            () => new ProcessOrchestrator(_camundaClientMock.Object, null));
        
        exception.Should().BeNull();
    }
}
