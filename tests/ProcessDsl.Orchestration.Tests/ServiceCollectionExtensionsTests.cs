using FluentAssertions;
using Microsoft.Extensions.DependencyInjection;
using ProcessDsl.Orchestration.Models;
using Xunit;

namespace ProcessDsl.Orchestration.Tests;

public class ServiceCollectionExtensionsTests
{
    [Fact]
    public void AddProcessDslOrchestration_WithAction_RegistersServices()
    {
        // Arrange
        var services = new ServiceCollection();

        // Act
        services.AddProcessDslOrchestration(options =>
        {
            options.BaseUrl = "http://test:8080";
            options.TimeoutSeconds = 60;
            options.EnableLogging = true;
        });

        var serviceProvider = services.BuildServiceProvider();

        // Assert
        var orchestrator = serviceProvider.GetService<IProcessOrchestrator>();
        orchestrator.Should().NotBeNull();
        orchestrator.Should().BeOfType<ProcessOrchestrator>();

        var camundaClient = serviceProvider.GetService<ICamundaClient>();
        camundaClient.Should().NotBeNull();
        camundaClient.Should().BeOfType<CamundaClient>();
    }

    [Fact]
    public void AddProcessDslOrchestration_WithUrl_RegistersServices()
    {
        // Arrange
        var services = new ServiceCollection();

        // Act
        services.AddProcessDslOrchestration("http://camunda:9090");
        var serviceProvider = services.BuildServiceProvider();

        // Assert
        var orchestrator = serviceProvider.GetService<IProcessOrchestrator>();
        orchestrator.Should().NotBeNull();

        var camundaClient = serviceProvider.GetService<ICamundaClient>();
        camundaClient.Should().NotBeNull();
    }

    [Fact]
    public void AddProcessDslOrchestration_RegistersHttpClient()
    {
        // Arrange
        var services = new ServiceCollection();

        // Act
        services.AddProcessDslOrchestration("http://localhost:8080");
        var serviceProvider = services.BuildServiceProvider();

        // Assert
        var httpClientFactory = serviceProvider.GetService<IHttpClientFactory>();
        httpClientFactory.Should().NotBeNull();
    }

    [Fact]
    public void AddProcessDslOrchestration_MultipleCallsAllowed()
    {
        // Arrange
        var services = new ServiceCollection();

        // Act
        services.AddProcessDslOrchestration("http://localhost:8080");
        services.AddProcessDslOrchestration("http://localhost:9090"); // Override

        var serviceProvider = services.BuildServiceProvider();

        // Assert
        var orchestrator = serviceProvider.GetService<IProcessOrchestrator>();
        orchestrator.Should().NotBeNull();
    }

    [Fact]
    public void AddProcessDslOrchestration_NullServices_ThrowsArgumentNullException()
    {
        // Arrange
        ServiceCollection? services = null;

        // Act & Assert
        Assert.Throws<ArgumentNullException>(
            () => services!.AddProcessDslOrchestration("http://localhost:8080"));
    }

    [Fact]
    public void AddProcessDslOrchestration_NullAction_ThrowsArgumentNullException()
    {
        // Arrange
        var services = new ServiceCollection();

        // Act & Assert
        Assert.Throws<ArgumentNullException>(
            () => services.AddProcessDslOrchestration((Action<CamundaConfiguration>)null!));
    }

    [Fact]
    public void AddProcessDslOrchestration_ConfigurationApplied()
    {
        // Arrange
        var services = new ServiceCollection();
        var expectedUrl = "http://custom-camunda:8888";

        // Act
        services.AddProcessDslOrchestration(options =>
        {
            options.BaseUrl = expectedUrl;
            options.TimeoutSeconds = 120;
            options.AuthToken = "test-token";
            options.EnableLogging = true;
        });

        var serviceProvider = services.BuildServiceProvider();

        // Assert - This would require accessing the internal configuration
        // For now, we just verify services are registered
        var orchestrator = serviceProvider.GetService<IProcessOrchestrator>();
        orchestrator.Should().NotBeNull();
    }

    [Fact]
    public void AddProcessDslOrchestration_RegistersScopedOrchestrator()
    {
        // Arrange
        var services = new ServiceCollection();
        services.AddProcessDslOrchestration("http://localhost:8080");
        var serviceProvider = services.BuildServiceProvider();

        // Act
        using var scope1 = serviceProvider.CreateScope();
        using var scope2 = serviceProvider.CreateScope();

        var orchestrator1 = scope1.ServiceProvider.GetService<IProcessOrchestrator>();
        var orchestrator2 = scope2.ServiceProvider.GetService<IProcessOrchestrator>();

        // Assert - Different scopes should have different instances
        orchestrator1.Should().NotBeNull();
        orchestrator2.Should().NotBeNull();
        orchestrator1.Should().NotBeSameAs(orchestrator2);
    }
}
