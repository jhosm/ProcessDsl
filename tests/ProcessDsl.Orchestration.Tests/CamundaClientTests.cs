using System.Net;
using System.Text;
using FluentAssertions;
using Microsoft.Extensions.Options;
using Moq;
using Moq.Protected;
using ProcessDsl.Orchestration.Models;
using Xunit;

namespace ProcessDsl.Orchestration.Tests;

public class CamundaClientTests
{
    private readonly Mock<HttpMessageHandler> _httpMessageHandlerMock;
    private readonly HttpClient _httpClient;
    private readonly CamundaConfiguration _config;

    public CamundaClientTests()
    {
        _httpMessageHandlerMock = new Mock<HttpMessageHandler>();
        _httpClient = new HttpClient(_httpMessageHandlerMock.Object);
        _config = new CamundaConfiguration
        {
            BaseUrl = "http://localhost:8080",
            TimeoutSeconds = 30
        };
    }

    [Fact]
    public async Task CreateProcessInstanceAsync_Success_ReturnsProcessInstance()
    {
        // Arrange
        var processKey = "process-entity-demo";
        var request = new StartProcessRequest
        {
            Variables = new Dictionary<string, object>
            {
                ["testVar"] = "testValue"
            },
            BusinessKey = "test-123"
        };

        var responseContent = @"{
            ""id"": ""12345"",
            ""definitionId"": ""process-entity-demo"",
            ""version"": 1,
            ""businessKey"": ""test-123""
        }";

        _httpMessageHandlerMock
            .Protected()
            .Setup<Task<HttpResponseMessage>>(
                "SendAsync",
                ItExpr.Is<HttpRequestMessage>(req =>
                    req.Method == HttpMethod.Post &&
                    req.RequestUri!.ToString().Contains($"/engine-rest/process-definition/key/{processKey}/start")),
                ItExpr.IsAny<CancellationToken>())
            .ReturnsAsync(new HttpResponseMessage
            {
                StatusCode = HttpStatusCode.OK,
                Content = new StringContent(responseContent, Encoding.UTF8, "application/json")
            });

        var client = new CamundaClient(_httpClient, Options.Create(_config));

        // Act
        var result = await client.CreateProcessInstanceAsync(processKey, request);

        // Assert
        result.Should().NotBeNull();
        result.ProcessInstanceKey.Should().Be(12345);
        result.BpmnProcessId.Should().Be("process-entity-demo");
        result.Version.Should().Be(1);
    }

    [Fact]
    public async Task CreateProcessInstanceAsync_HttpError_ThrowsException()
    {
        // Arrange
        var processKey = "invalid-process";
        var request = new StartProcessRequest();

        _httpMessageHandlerMock
            .Protected()
            .Setup<Task<HttpResponseMessage>>(
                "SendAsync",
                ItExpr.IsAny<HttpRequestMessage>(),
                ItExpr.IsAny<CancellationToken>())
            .ReturnsAsync(new HttpResponseMessage
            {
                StatusCode = HttpStatusCode.NotFound,
                Content = new StringContent("Process not found")
            });

        var client = new CamundaClient(_httpClient, Options.Create(_config));

        // Act & Assert
        await Assert.ThrowsAsync<HttpRequestException>(
            () => client.CreateProcessInstanceAsync(processKey, request));
    }

    [Fact]
    public async Task CreateProcessInstanceAsync_NullProcessKey_ThrowsArgumentException()
    {
        // Arrange
        var client = new CamundaClient(_httpClient, Options.Create(_config));
        var request = new StartProcessRequest();

        // Act & Assert
        await Assert.ThrowsAsync<ArgumentException>(
            () => client.CreateProcessInstanceAsync(null!, request));
    }

    [Fact]
    public async Task CreateProcessInstanceAsync_NullRequest_ThrowsArgumentNullException()
    {
        // Arrange
        var client = new CamundaClient(_httpClient, Options.Create(_config));

        // Act & Assert
        await Assert.ThrowsAsync<ArgumentNullException>(
            () => client.CreateProcessInstanceAsync("test-process", null!));
    }

    [Fact]
    public async Task CreateProcessInstanceWithEntityAsync_Success_ReturnsProcessInstance()
    {
        // Arrange
        var processKey = "process-entity-demo";
        var entityData = new { Id = "123", Name = "Test Customer" };

        var responseContent = @"{
            ""id"": ""67890"",
            ""definitionId"": ""process-entity-demo"",
            ""version"": 2
        }";

        _httpMessageHandlerMock
            .Protected()
            .Setup<Task<HttpResponseMessage>>(
                "SendAsync",
                ItExpr.IsAny<HttpRequestMessage>(),
                ItExpr.IsAny<CancellationToken>())
            .ReturnsAsync(new HttpResponseMessage
            {
                StatusCode = HttpStatusCode.OK,
                Content = new StringContent(responseContent, Encoding.UTF8, "application/json")
            });

        var client = new CamundaClient(_httpClient, Options.Create(_config));

        // Act
        var result = await client.CreateProcessInstanceWithEntityAsync(processKey, entityData);

        // Assert
        result.Should().NotBeNull();
        result.ProcessInstanceKey.Should().Be(67890);
        result.BpmnProcessId.Should().Be("process-entity-demo");
        result.Version.Should().Be(2);
    }

    [Fact]
    public void Constructor_WithAuthToken_AddsAuthorizationHeader()
    {
        // Arrange
        var configWithAuth = new CamundaConfiguration
        {
            BaseUrl = "http://localhost:8080",
            AuthToken = "test-token-123"
        };

        // Act
        var client = new CamundaClient(_httpClient, Options.Create(configWithAuth));

        // Assert
        _httpClient.DefaultRequestHeaders.Authorization?.Scheme.Should().Be("Bearer");
        _httpClient.DefaultRequestHeaders.Authorization?.Parameter.Should().Be("test-token-123");
    }

    [Fact]
    public void Constructor_NullHttpClient_ThrowsArgumentNullException()
    {
        // Act & Assert
        Assert.Throws<ArgumentNullException>(
            () => new CamundaClient(null!, Options.Create(_config)));
    }

    [Fact]
    public void Constructor_NullConfig_ThrowsArgumentNullException()
    {
        // Act & Assert
        Assert.Throws<ArgumentNullException>(
            () => new CamundaClient(_httpClient, null!));
    }
}
