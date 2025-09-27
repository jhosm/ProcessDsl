import { ZBClient } from 'zeebe-node';
import * as fs from 'fs';
import * as path from 'path';

// Initialize Zeebe client for local development (insecure)
const zbc = new ZBClient('localhost:26500', {
  useTLS: false
});

async function testWorkflow() {
  try {
    console.log('🔄 Connecting to Zeebe...');
    
    // Check Zeebe status
    const topology = await zbc.topology();
    console.log('✅ Connected to Zeebe cluster');
    console.log(`   Brokers: ${topology.brokers.length}`);
    console.log(`   Cluster Size: ${topology.clusterSize}`);
    
    // Read and deploy the BPMN file
    console.log('\n📄 Deploying BPMN process...');
    const bpmnPath = path.join(__dirname, 'service_task_demo.bpmn');
    
    if (!fs.existsSync(bpmnPath)) {
      throw new Error(`BPMN file not found at: ${bpmnPath}`);
    }
    
    const deployment = await zbc.deployProcess(bpmnPath);
    console.log('✅ Process deployed successfully');
    console.log(`   Process ID: ${deployment.processes[0].bpmnProcessId}`);
    console.log(`   Version: ${deployment.processes[0].version}`);
    
    // Create a process instance with test data
    console.log('\n🚀 Creating process instance...');
    const processInstance = await zbc.createProcessInstance({
      bpmnProcessId: 'payment-process',
      variables: {
        amount: 99.99,
        cardNumber: '4532015112830366', // Valid test card number
        cvv: '123',
        customerEmail: 'test@example.com'
      }
    });
    
    console.log('✅ Process instance created successfully');
    console.log(`   Instance Key: ${processInstance.processInstanceKey}`);
    console.log(`   Process Definition Key: ${processInstance.processDefinitionKey}`);
    
    console.log('\n🎯 Process instance is now running!');
    console.log('   Check your job workers console for processing logs...');
    
    // Wait a bit to see some processing
    console.log('\n⏳ Waiting 10 seconds to observe job processing...');
    await new Promise(resolve => setTimeout(resolve, 10000));
    
    console.log('\n✨ Test completed! Check the job workers output for results.');
    
  } catch (error: any) {
    console.error('❌ Error:', error.message || error);
    if (error.code) {
      console.error(`   Error Code: ${error.code}`);
    }
  } finally {
    await zbc.close();
    console.log('\n🔌 Disconnected from Zeebe');
  }
}

// Run the test
testWorkflow().catch(console.error);
