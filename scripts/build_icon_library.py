"""Build the comprehensive technology icon library.

Downloads official icons from vendor repositories and community packs,
normalizes them to square PNGs, and generates the master registry.json.

Sources:
  - AWS: awslabs/aws-icons-for-plantuml (868 official architecture PNGs)
  - Azure: nicolaparo/azure-icons (311 official icons pre-rendered to PNG)
  - Third-party: cdn.simpleicons.org (SVG for OSS/vendor tools)
  - Power BI: marclelijveld/Power-BI-Icons

Usage:
    py scripts/build_icon_library.py                   # download all
    py scripts/build_icon_library.py --category aws    # just AWS
    py scripts/build_icon_library.py --report          # coverage report
    py scripts/build_icon_library.py --validate        # run validation
    py scripts/build_icon_library.py --registry-only   # rebuild registry
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT / "assets" / "icons"
REGISTRY_PATH = ASSETS_DIR / "registry.json"

try:
    from PIL import Image
    import io as _io
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

try:
    import cairosvg
    HAS_CAIROSVG = True
except ImportError:
    HAS_CAIROSVG = False

# Mirror used when the primary simpleicons.org CDN is unreachable (e.g. a
# restrictive network policy) — same open-source icon set, served from
# GitHub instead.
SIMPLE_ICONS_GITHUB_MIRROR = "https://raw.githubusercontent.com/simple-icons/simple-icons/develop/icons"


# ═══════════════════════════════════════════════════════════════════
# URL Bases
# ═══════════════════════════════════════════════════════════════════

AWS_BASE = "https://raw.githubusercontent.com/awslabs/aws-icons-for-plantuml/main/dist"
AZURE_BASE = "https://raw.githubusercontent.com/nicolaparo/azure-icons/main/256"
PBI_BASE = "https://raw.githubusercontent.com/marclelijveld/Power-BI-Icons/master/PNG"
SIMPLE_ICONS = "https://cdn.simpleicons.org"


# ═══════════════════════════════════════════════════════════════════
# AWS: complete catalog from awslabs/aws-icons-for-plantuml
# Organized by official AWS category → list of PNG filenames
# ═══════════════════════════════════════════════════════════════════

AWS_CATEGORIES: dict[str, list[str]] = {
    "Analytics": ["Analytics.png", "Athena.png", "AthenaDataSourceConnectors.png", "CleanRooms.png", "CloudSearch.png", "CloudSearchSearchDocuments.png", "DataExchange.png", "DataExchangeforAPIs.png", "DataFirehose.png", "DataZone.png", "DataZoneBusinessDataCatalog.png", "DataZoneDataPortal.png", "DataZoneDataProjects.png", "EMR.png", "EMRCluster.png", "EMREMREngine.png", "EMRHDFSCluster.png", "EntityResolution.png", "FinSpace.png", "Glue.png", "GlueAWSGlueforRay.png", "GlueCrawler.png", "GlueDataBrew.png", "GlueDataCatalog.png", "GlueDataQuality.png", "Kinesis.png", "KinesisDataStreams.png", "KinesisVideoStreams.png", "LakeFormation.png", "LakeFormationDataLake.png", "ManagedServiceforApacheFlink.png", "ManagedStreamingforApacheKafka.png", "MSKAmazonMSKConnect.png", "OpenSearchService.png", "OpenSearchServiceClusterAdministratorNode.png", "OpenSearchServiceDataNode.png", "OpenSearchServiceIndex.png", "OpenSearchServiceObservability.png", "OpenSearchServiceOpenSearchDashboards.png", "OpenSearchServiceOpenSearchIngestion.png", "OpenSearchServiceTraces.png", "OpenSearchServiceUltraWarmNode.png", "Redshift.png", "RedshiftAutocopy.png", "RedshiftDataSharingGovernance.png", "RedshiftDenseComputeNode.png", "RedshiftDenseStorageNode.png", "RedshiftML.png", "RedshiftQueryEditorv20.png", "RedshiftRA3.png", "RedshiftStreamingIngestion.png", "SageMaker.png"],
    "ApplicationIntegration": ["AppFlow.png", "ApplicationIntegration.png", "AppSync.png", "B2BDataInterchange.png", "EventBridge.png", "EventBridgeCustomEventBus.png", "EventBridgeDefaultEventBus.png", "EventBridgeEvent.png", "EventBridgePipes.png", "EventBridgeRule.png", "EventBridgeSaasPartnerEvent.png", "EventBridgeScheduler.png", "EventBridgeSchema.png", "EventBridgeSchemaRegistry.png", "ExpressWorkflows.png", "ManagedWorkflowsforApacheAirflow.png", "MQ.png", "MQBroker.png", "SimpleNotificationService.png", "SimpleNotificationServiceEmailNotification.png", "SimpleNotificationServiceHTTPNotification.png", "SimpleNotificationServiceTopic.png", "SimpleQueueService.png", "SimpleQueueServiceMessage.png", "SimpleQueueServiceQueue.png", "StepFunctions.png"],
    "ArtificialIntelligence": ["ApacheMXNetonAWS.png", "AppStudio.png", "ArtificialIntelligence.png", "AugmentedAIA2I.png", "Bedrock.png", "BedrockAgentCore.png", "CodeGuru.png", "CodeWhisperer.png", "Comprehend.png", "ComprehendMedical.png", "DeepLearningAMIs.png", "DeepLearningContainers.png", "DeepRacer.png", "DevOpsGuru.png", "DevOpsGuruInsights.png", "ElasticInference.png", "Forecast.png", "FraudDetector.png", "HealthImaging.png", "HealthLake.png", "HealthOmics.png", "HealthScribe.png", "Kendra.png", "Lex.png", "LookoutforEquipment.png", "LookoutforVision.png", "Monitron.png", "Neuron.png", "Nova.png", "Panorama.png", "Personalize.png", "Polly.png", "PyTorchonAWS.png", "Q.png", "Rekognition.png", "RekognitionImage.png", "RekognitionVideo.png", "SageMakerAI.png", "SageMakerAICanvas.png", "SageMakerAIGeospatialML.png", "SageMakerAIModel.png", "SageMakerAINotebook.png", "SageMakerAIShadowTesting.png", "SageMakerAITrain.png", "SageMakerGroundTruth.png", "SageMakerStudioLab.png", "TensorFlowonAWS.png", "Textract.png", "TextractAnalyzeLending.png", "Transcribe.png", "Translate.png"],
    "Blockchain": ["Blockchain.png", "ManagedBlockchain.png", "ManagedBlockchainBlockchain.png"],
    "BusinessApplications": ["AppFabric.png", "BusinessApplications.png", "Chime.png", "ChimeSDK.png", "Connect.png", "EndUserMessaging.png", "Pinpoint.png", "PinpointAPIs.png", "PinpointJourney.png", "QuickSuite.png", "SimpleEmailService.png", "SimpleEmailServiceEmail.png", "SupplyChain.png", "Wickr.png", "WorkDocs.png", "WorkDocsSDK.png", "WorkMail.png"],
    "CloudFinancialManagement": ["BillingConductor.png", "Budgets.png", "CloudFinancialManagement.png", "CostandUsageReport.png", "CostExplorer.png", "ReservedInstanceReporting.png", "SavingsPlans.png"],
    "Compute": ["AppRunner.png", "Batch.png", "Bottlerocket.png", "Compute.png", "ComputeOptimizer2.png", "DCV.png", "EC2.png", "EC2AMI.png", "EC2AutoScaling.png", "EC2AutoScalingResource.png", "EC2AWSMicroserviceExtractorforNET.png", "EC2DBInstance.png", "EC2ElasticIPAddress.png", "EC2ImageBuilder.png", "EC2Instance.png", "EC2Instances.png", "EC2InstancewithCloudWatch.png", "EC2Rescue.png", "EC2SpotInstance.png", "ElasticBeanstalk.png", "ElasticBeanstalkApplication.png", "ElasticBeanstalkDeployment.png", "ElasticFabricAdapter.png", "ElasticVMwareService.png", "Lambda.png", "LambdaLambdaFunction.png", "Lightsail.png", "LightsailforResearch.png", "LocalZones.png", "NitroEnclaves.png", "Outpostsfamily.png", "Outpostsrack.png", "Outpostsservers.png", "ParallelCluster.png", "ParallelComputingService.png", "ServerlessApplicationRepository.png", "SimSpaceWeaver.png", "Wavelength.png"],
    "Containers": ["Containers.png", "ECSAnywhere.png", "EKSAnywhere.png", "EKSDistro.png", "ElasticContainerRegistry.png", "ElasticContainerRegistryImage.png", "ElasticContainerRegistryRegistry.png", "ElasticContainerService.png", "ElasticContainerServiceContainer1.png", "ElasticContainerServiceContainer2.png", "ElasticContainerServiceContainer3.png", "ElasticContainerServiceCopilotCLI.png", "ElasticContainerServiceECSServiceConnect.png", "ElasticContainerServiceService.png", "ElasticContainerServiceTask.png", "ElasticKubernetesService.png", "ElasticKubernetesServiceEKSonOutposts.png", "Fargate.png", "RedHatOpenShiftServiceonAWS.png"],
    "CustomerEnablement": ["Activate.png", "CustomerEnablement.png", "IQ.png", "ManagedServices.png", "ProfessionalServices.png", "rePost.png", "rePostPrivate.png", "Support.png", "TrainingCertification.png"],
    "CustomerExperience": ["CustomerExperience.png"],
    "Database": ["Aurora.png", "AuroraAmazonAuroraInstanceAlternate.png", "AuroraAmazonRDSInstance.png", "AuroraAmazonRDSInstanceAlternate.png", "AuroraInstance.png", "AuroraMariaDBInstance.png", "AuroraMariaDBInstanceAlternate.png", "AuroraMySQLInstance.png", "AuroraMySQLInstanceAlternate.png", "AuroraOracleInstance.png", "AuroraOracleInstanceAlternate.png", "AuroraPIOPSInstance.png", "AuroraPostgreSQLInstance.png", "AuroraPostgreSQLInstanceAlternate.png", "AuroraSQLServerInstance.png", "AuroraSQLServerInstanceAlternate.png", "AuroraTrustedLanguageExtensionsforPostgreSQL.png", "Database.png", "DatabaseMigrationService.png", "DatabaseMigrationServiceDatabasemigrationworkflowjob.png", "DocumentDB.png", "DocumentDBElasticClusters.png", "DynamoDB.png", "DynamoDBAmazonDynamoDBAccelerator.png", "DynamoDBAttribute.png", "DynamoDBAttributes.png", "DynamoDBGlobalsecondaryindex.png", "DynamoDBItem.png", "DynamoDBItems.png", "DynamoDBStandardAccessTableClass.png", "DynamoDBStandardInfrequentAccessTableClass.png", "DynamoDBStream.png", "DynamoDBTable.png", "ElastiCache.png", "ElastiCacheCacheNode.png", "ElastiCacheElastiCacheforMemcached.png", "ElastiCacheElastiCacheforRedis.png", "ElastiCacheElastiCacheforValkey.png", "Keyspaces.png", "MemoryDB.png", "Neptune.png", "OracleDatabaseatAWS.png", "RDS.png", "RDSBlueGreenDeployments.png", "RDSMultiAZ.png", "RDSMultiAZDBCluster.png", "RDSOptimizedWrites.png", "RDSProxyInstance.png", "RDSProxyInstanceAlternate.png", "RDSTrustedLanguageExtensionsforPostgreSQL.png", "Timestream.png"],
    "DeveloperTools": ["Cloud9.png", "Cloud9Cloud9.png", "CloudControlAPI.png", "CloudDevelopmentKit.png", "CloudShell.png", "CodeArtifact.png", "CodeBuild.png", "CodeCatalyst.png", "CodeCommit.png", "CodeDeploy.png", "CodePipeline.png", "CommandLineInterface.png", "Corretto.png", "DeveloperTools.png", "FaultInjectionService.png", "InfrastructureComposer.png", "ToolsandSDKs.png", "XRay.png"],
    "EndUserComputing": ["EndUserComputing.png", "WorkSpaces.png"],
    "FrontEndWebMobile": ["Amplify.png", "AmplifyAWSAmplifyStudio.png", "DeviceFarm.png", "FrontEndWebMobile.png", "LocationService.png", "LocationServiceGeofence.png", "LocationServiceMap.png", "LocationServicePlace.png", "LocationServiceRoutes.png", "LocationServiceTrack.png"],
    "Games": ["GameLiftServers.png", "GameLiftStreams.png", "Games.png", "Open3DEngine.png"],
    "General": ["Alert.png", "Alert_Dark.png", "AuthenticatedUser.png", "AuthenticatedUser_Dark.png", "AWSManagementConsole.png", "AWSManagementConsole_Dark.png", "Camera.png", "Camera_Dark.png", "Chat.png", "Chat_Dark.png", "Client.png", "Client_Dark.png", "ColdStorage.png", "ColdStorage_Dark.png", "Credentials.png", "Credentials_Dark.png", "DataStream.png", "DataStream_Dark.png", "DataTable.png", "DataTable_Dark.png", "Disk.png", "Disk_Dark.png", "Document.png", "Document_Dark.png", "Documents.png", "Documents_Dark.png", "Email.png", "Email_Dark.png", "Firewall.png", "Firewall_Dark.png", "Folder.png", "Folder_Dark.png", "Folders.png", "Folders_Dark.png", "Forums.png", "Forums_Dark.png", "Gear.png", "Gear_Dark.png", "GenericApplication.png", "GenericApplication_Dark.png", "Genericdatabase.png", "Genericdatabase_Dark.png", "GitRepository.png", "GitRepository_Dark.png", "Globe.png", "Globe_Dark.png", "Internet.png", "Internet_Dark.png", "Internetalt1.png", "Internetalt1_Dark.png", "Internetalt2.png", "Internetalt2_Dark.png", "JSONScript.png", "JSONScript_Dark.png", "Logs.png", "Logs_Dark.png", "MagnifyingGlass.png", "MagnifyingGlass_Dark.png", "Marketplace.png", "Marketplace_Dark.png", "Metrics.png", "Metrics_Dark.png", "Mobileclient.png", "Mobileclient_Dark.png", "Multimedia.png", "Multimedia_Dark.png", "Officebuilding.png", "Officebuilding_Dark.png", "ProgrammingLanguage.png", "ProgrammingLanguage_Dark.png", "Question.png", "Question_Dark.png", "Recover.png", "Recover_Dark.png", "SAMLtoken.png", "SAMLtoken_Dark.png", "SDK.png", "SDK_Dark.png", "Servers.png", "Servers_Dark.png", "Shield2.png", "Shield2_Dark.png", "SourceCode.png", "SourceCode_Dark.png", "SSLpadlock.png", "SSLpadlock_Dark.png", "Tapestorage.png", "Tapestorage_Dark.png", "Toolkit.png", "Toolkit_Dark.png", "Traditionalserver.png", "Traditionalserver_Dark.png", "User.png", "User_Dark.png", "Users.png", "Users_Dark.png"],
    "Groups": ["AutoScalingGroup.png", "AWSAccount.png", "AWSCloud.png", "AWSCloud_Dark.png", "AWSCloudAlt.png", "AWSCloudAlt_Dark.png", "CorporateDataCenter.png", "EC2InstanceContents.png", "ElasticBeanstalkContainer.png", "GenericBlue.png", "GenericGreen.png", "GenericOrange.png", "GenericPink.png", "GenericPurple.png", "GenericRed.png", "GenericTurquoise.png", "IoTGreengrass.png", "IoTGreengrassDeployment.png", "PrivateSubnet.png", "PublicSubnet.png", "Region.png", "ServerContents.png", "SpotFleet.png", "StepFunctionsWorkflow.png", "VPC.png"],
    "InternetOfThings": ["FreeRTOS.png", "InternetOfThings.png", "IoTAction.png", "IoTActuator.png", "IoTAlexaEnabledDevice.png", "IoTAlexaSkill.png", "IoTAlexaVoiceService.png", "IoTCertificate.png", "IoTCore.png", "IoTCoreDeviceAdvisor.png", "IoTCoreDeviceLocation.png", "IoTDesiredState.png", "IoTDeviceDefender.png", "IoTDeviceDefenderIoTDeviceJobs.png", "IoTDeviceGateway.png", "IoTDeviceManagement.png", "IoTDeviceManagementFleetHub.png", "IoTDeviceTester.png", "IoTEcho.png", "IoTEvents.png", "IoTExpressLink.png", "IoTFireTV.png", "IoTFireTVStick.png", "IoTFleetWise.png", "IoTGreengrass.png", "IoTGreengrassArtifact.png", "IoTGreengrassComponent.png", "IoTGreengrassComponentMachineLearning.png", "IoTGreengrassComponentNucleus.png", "IoTGreengrassComponentPrivate.png", "IoTGreengrassComponentPublic.png", "IoTGreengrassConnector.png", "IoTGreengrassInterprocessCommunication.png", "IoTGreengrassProtocol.png", "IoTGreengrassRecipe.png", "IoTGreengrassStreamManager.png", "IoTHardwareBoard.png", "IoTHTTP2Protocol.png", "IoTHTTPProtocol.png", "IoTLambdaFunction.png", "IoTLoRaWANProtocol.png", "IoTMQTTProtocol.png", "IoTOverAirUpdate.png", "IoTPolicy.png", "IoTReportedState.png", "IoTRule.png", "IoTSailboat.png", "IoTSensor.png", "IoTServo.png", "IoTShadow.png", "IoTSimulator.png", "IoTSiteWise.png", "IoTSiteWiseAsset.png", "IoTSiteWiseAssetHierarchy.png", "IoTSiteWiseAssetModel.png", "IoTSiteWiseAssetProperties.png", "IoTSiteWiseDataStreams.png", "IoTThingBank.png", "IoTThingBicycle.png", "IoTThingCamera.png", "IoTThingCar.png", "IoTThingCart.png", "IoTThingCoffeePot.png", "IoTThingDoorLock.png", "IoTThingFactory.png", "IoTThingFreeRTOSDevice.png", "IoTThingGeneric.png", "IoTThingHouse.png", "IoTThingHumiditySensor.png", "IoTThingIndustrialPC.png", "IoTThingLightbulb.png", "IoTThingMedicalEmergency.png", "IoTThingPLC.png", "IoTThingPoliceEmergency.png", "IoTThingRelay.png", "IoTThingStacklight.png", "IoTThingTemperatureHumiditySensor.png", "IoTThingTemperatureSensor.png", "IoTThingTemperatureVibrationSensor.png", "IoTThingThermostat.png", "IoTThingTravel.png", "IoTThingUtility.png", "IoTThingVibrationSensor.png", "IoTThingWindfarm.png", "IoTTopic.png", "IoTTwinMaker.png"],
    "ManagementGovernance": ["AppConfig.png", "ApplicationAutoScaling2.png", "AutoScaling.png", "BackintAgent.png", "Chatbot.png", "CloudFormation.png", "CloudFormationChangeSet.png", "CloudFormationStack.png", "CloudFormationTemplate.png", "CloudTrail.png", "CloudTrailCloudTrailLake.png", "CloudWatch.png", "CloudWatchAlarm.png", "CloudWatchCrossaccountObservability.png", "CloudWatchDataProtection.png", "CloudWatchEventEventBased.png", "CloudWatchEventTimeBased.png", "CloudWatchEvidently.png", "CloudWatchLogs.png", "CloudWatchMetricsInsights.png", "CloudWatchRule.png", "CloudWatchRUM.png", "CloudWatchSynthetics.png", "ComputeOptimizer.png", "Config.png", "ConsoleMobileApplication.png", "ControlTower.png", "DevOpsAgent.png", "DistroforOpenTelemetry.png", "HealthDashboard.png", "LaunchWizard.png", "LicenseManager.png", "LicenseManagerApplicationDiscovery.png", "LicenseManagerLicenseBlending.png", "ManagedGrafana.png", "ManagedServiceforPrometheus.png", "ManagementConsole.png", "ManagementGovernance.png", "Organizations.png", "OrganizationsAccount.png", "OrganizationsManagementAccount.png", "OrganizationsOrganizationalUnit.png", "PartnerCentral.png", "Proton.png", "ResilienceHub.png", "ResourceExplorer.png", "ServiceCatalog.png", "ServiceManagementConnector.png", "SystemsManager.png", "SystemsManagerApplicationManager.png", "SystemsManagerAutomation.png", "SystemsManagerChangeCalendar.png", "SystemsManagerChangeManager.png", "SystemsManagerCompliance.png", "SystemsManagerDistributor.png", "SystemsManagerDocuments.png", "SystemsManagerIncidentManager.png", "SystemsManagerInventory.png", "SystemsManagerMaintenanceWindows.png", "SystemsManagerOpsCenter.png", "SystemsManagerParameterStore.png", "SystemsManagerPatchManager.png", "SystemsManagerRunCommand.png", "SystemsManagerSessionManager.png", "SystemsManagerStateManager.png", "TelcoNetworkBuilder.png", "TrustedAdvisor.png", "TrustedAdvisorChecklist.png", "TrustedAdvisorChecklistCost.png", "TrustedAdvisorChecklistFaultTolerant.png", "TrustedAdvisorChecklistPerformance.png", "TrustedAdvisorChecklistSecurity.png", "UserNotifications.png", "WellArchitectedTool.png"],
    "MediaServices": ["CloudDigitalInterface.png", "DeadlineCloud.png", "ElementalAppliancesSoftware.png", "ElementalConductor.png", "ElementalDelta.png", "ElementalLink.png", "ElementalLive.png", "ElementalMediaConnect.png", "ElementalMediaConnectMediaConnectGateway.png", "ElementalMediaConvert.png", "ElementalMediaLive.png", "ElementalMediaPackage.png", "ElementalMediaStore.png", "ElementalMediaTailor.png", "ElementalServer.png", "InteractiveVideoService.png", "KinesisVideoStreams2.png", "MediaServices.png", "ThinkboxDeadline.png", "ThinkboxFrost.png", "ThinkboxKrakatoa.png", "ThinkboxStoke.png", "ThinkboxXMesh.png"],
    "MigrationModernization": ["ApplicationDiscoveryService.png", "ApplicationDiscoveryServiceAWSAgentlessCollector.png", "ApplicationDiscoveryServiceAWSDiscoveryAgent.png", "ApplicationDiscoveryServiceMigrationEvaluatorCollector.png", "ApplicationMigrationService.png", "DataSync.png", "DatasyncAgent.png", "DataSyncDiscovery.png", "DataTransferTerminal.png", "MainframeModernization.png", "MainframeModernizationAnalyzer.png", "MainframeModernizationCompiler.png", "MainframeModernizationConverter.png", "MainframeModernizationDeveloper.png", "MainframeModernizationRuntime.png", "MigrationEvaluator.png", "MigrationHub.png", "MigrationHubRefactorSpacesApplications.png", "MigrationHubRefactorSpacesEnvironments.png", "MigrationHubRefactorSpacesServices.png", "MigrationModernization.png", "TransferFamily.png", "TransferFamilyAWSAS2.png", "TransferFamilyAWSFTP.png", "TransferFamilyAWSFTPS.png", "TransferFamilyAWSSFTP.png", "Transform.png"],
    "MulticloudandHybrid": ["MulticloudandHybrid.png"],
    "NetworkingContentDelivery": ["APIGateway.png", "APIGatewayEndpoint.png", "ApplicationRecoveryController.png", "AppMesh.png", "AppMeshMesh.png", "AppMeshVirtualGateway.png", "AppMeshVirtualNode.png", "AppMeshVirtualRouter.png", "AppMeshVirtualService.png", "ClientVPN.png", "CloudFront.png", "CloudFrontDownloadDistribution.png", "CloudFrontEdgeLocation.png", "CloudFrontFunctions.png", "CloudFrontStreamingDistribution.png", "CloudMap.png", "CloudMapNamespace.png", "CloudMapResource.png", "CloudMapService.png", "CloudWAN.png", "CloudWANCoreNetworkEdge.png", "CloudWANSegmentNetwork.png", "CloudWANTransitGatewayRouteTableAttachment.png", "DirectConnect.png", "DirectConnectGateway.png", "ElasticLoadBalancing.png", "ElasticLoadBalancingApplicationLoadBalancer.png", "ElasticLoadBalancingClassicLoadBalancer.png", "ElasticLoadBalancingGatewayLoadBalancer.png", "ElasticLoadBalancingNetworkLoadBalancer.png", "GlobalAccelerator.png", "NetworkingContentDelivery.png", "PrivateLink.png", "Route53.png", "Route53HostedZone.png", "Route53ReadinessChecks.png", "Route53Resolver.png", "Route53ResolverDNSFirewall.png", "Route53ResolverQueryLogging.png", "Route53RouteTable.png", "Route53RoutingControls.png", "RTBFabric.png", "SitetoSiteVPN.png", "TransitGateway.png", "TransitGatewayAttachment.png", "VerifiedAccess.png", "VirtualPrivateCloud.png", "VPCCarrierGateway.png", "VPCCustomerGateway.png", "VPCElasticNetworkAdapter.png", "VPCElasticNetworkInterface.png", "VPCEndpoints.png", "VPCFlowLogs.png", "VPCInternetGateway.png", "VPCLattice.png", "VPCNATGateway.png", "VPCNetworkAccessAnalyzer.png", "VPCNetworkAccessControlList.png", "VPCPeeringConnection.png", "VPCReachabilityAnalyzer.png", "VPCRouter.png", "VPCTrafficMirroring.png", "VPCVirtualprivatecloudVPC.png", "VPCVPNConnection.png", "VPCVPNGateway.png"],
    "QuantumTechnologies": ["Braket.png", "BraketChandelier.png", "BraketChip.png", "BraketEmbeddedSimulator.png", "BraketManagedSimulator.png", "BraketNoiseSimulator.png", "BraketQPU.png", "BraketSimulator.png", "BraketSimulator1.png", "BraketSimulator2.png", "BraketSimulator3.png", "BraketSimulator4.png", "BraketStateVector.png", "BraketTensorNetwork.png", "QuantumTechnologies.png"],
    "Satellite": ["GroundStation.png", "Satellite.png"],
    "SecurityIdentityCompliance": ["Artifact.png", "AuditManager.png", "CertificateManager.png", "CertificateManagerCertificateAuthority.png", "CloudDirectory.png", "CloudHSM.png", "Cognito.png", "Detective.png", "DirectoryService.png", "DirectoryServiceADConnector.png", "DirectoryServiceAWSManagedMicrosoftAD.png", "DirectoryServiceSimpleAD.png", "FirewallManager.png", "GuardDuty.png", "IAMIdentityCenter.png", "IdentityAccessManagementAddon.png", "IdentityAccessManagementAWSSTS.png", "IdentityAccessManagementAWSSTSAlternate.png", "IdentityAccessManagementDataEncryptionKey.png", "IdentityAccessManagementEncryptedData.png", "IdentityAccessManagementIAMAccessAnalyzer.png", "IdentityAccessManagementIAMRolesAnywhere.png", "IdentityAccessManagementLongTermSecurityCredential.png", "IdentityAccessManagementMFAToken.png", "IdentityAccessManagementPermissions.png", "IdentityAccessManagementRole.png", "IdentityAccessManagementTemporarySecurityCredential.png", "IdentityandAccessManagement.png", "Inspector.png", "InspectorAgent.png", "KeyManagementService.png", "KeyManagementServiceExternalKeyStore.png", "Macie.png", "NetworkFirewall.png", "NetworkFirewallEndpoints.png", "PaymentCryptography.png", "PrivateCertificateAuthority.png", "ResourceAccessManager.png", "SecretsManager.png", "SecurityAgent.png", "SecurityHub.png", "SecurityHubFinding.png", "SecurityIdentityCompliance.png", "SecurityIncidentResponse.png", "SecurityLake.png", "Shield.png", "ShieldAWSShieldAdvanced.png", "Signer.png", "VerifiedPermissions.png", "WAF.png", "WAFBadBot.png", "WAFBot.png", "WAFBotControl.png", "WAFFilteringRule.png", "WAFLabels.png", "WAFManagedRule.png", "WAFRule.png"],
    "Serverless": ["Serverless.png"],
    "Storage": ["Backup.png", "BackupAuditManager.png", "BackupAWSBackupforAWSCloudFormation.png", "BackupAWSBackupsupportforAmazonFSxforNetAppONTAP.png", "BackupAWSBackupsupportforAmazonS3.png", "BackupAWSBackupsupportforVMwareWorkloads.png", "BackupBackupPlan.png", "BackupBackupRestore.png", "BackupBackupVault.png", "BackupComplianceReporting.png", "BackupCompute.png", "BackupDatabase.png", "BackupGateway.png", "BackupLegalHold.png", "BackupRecoveryPointObjective.png", "BackupRecoveryTimeObjective.png", "BackupStorage.png", "BackupVaultLock.png", "BackupVirtualMachine.png", "BackupVirtualMachineMonitor.png", "EFS.png", "ElasticBlockStore.png", "ElasticBlockStoreAmazonDataLifecycleManager.png", "ElasticBlockStoreMultipleVolumes.png", "ElasticBlockStoreSnapshot.png", "ElasticBlockStoreVolume.png", "ElasticBlockStoreVolumegp3.png", "ElasticDisasterRecovery.png", "ElasticFileSystemElasticThroughput.png", "ElasticFileSystemFileSystem.png", "ElasticFileSystemIntelligentTiering.png", "ElasticFileSystemOneZone.png", "ElasticFileSystemOneZoneInfrequentAccess.png", "ElasticFileSystemStandard.png", "ElasticFileSystemStandardInfrequentAccess.png", "FileCache.png", "FileCacheHybridNFSlinkeddatasets.png", "FileCacheOnpremisesNFSlinkeddatasets.png", "FileCacheS3linkeddatasets.png", "FSx.png", "FSxforLustre.png", "FSxforNetAppONTAP.png", "FSxforOpenZFS.png", "FSxforWFS.png", "S3onOutposts.png", "SimpleStorageService.png", "SimpleStorageServiceBucket.png", "SimpleStorageServiceBucketWithObjects.png", "SimpleStorageServiceDirectoryBucket.png", "SimpleStorageServiceGeneralAccessPoints.png", "SimpleStorageServiceGlacier.png", "SimpleStorageServiceGlacierArchive.png", "SimpleStorageServiceGlacierVault.png", "SimpleStorageServiceObject.png", "SimpleStorageServiceS3BatchOperations.png", "SimpleStorageServiceS3ExpressOneZone.png", "SimpleStorageServiceS3GlacierDeepArchive.png", "SimpleStorageServiceS3GlacierFlexibleRetrieval.png", "SimpleStorageServiceS3GlacierInstantRetrieval.png", "SimpleStorageServiceS3IntelligentTiering.png", "SimpleStorageServiceS3MultiRegionAccessPoints.png", "SimpleStorageServiceS3ObjectLambda.png", "SimpleStorageServiceS3ObjectLambdaAccessPoints.png", "SimpleStorageServiceS3ObjectLock.png", "SimpleStorageServiceS3OneZoneIA.png", "SimpleStorageServiceS3OnOutposts.png", "SimpleStorageServiceS3Replication.png", "SimpleStorageServiceS3ReplicationTimeControl.png", "SimpleStorageServiceS3Select.png", "SimpleStorageServiceS3Standard.png", "SimpleStorageServiceS3StandardIA.png", "SimpleStorageServiceS3StorageLens.png", "SimpleStorageServiceS3Tables.png", "SimpleStorageServiceS3Vectors.png", "SimpleStorageServiceVPCAccessPoints.png", "Snowball.png", "SnowballEdge.png", "SnowballSnowballImportExport.png", "Storage.png", "StorageGateway.png", "StorageGatewayAmazonFSxFileGateway.png", "StorageGatewayAmazonS3FileGateway.png", "StorageGatewayCachedVolume.png", "StorageGatewayFileGateway.png", "StorageGatewayNoncachedVolume.png", "StorageGatewayTapeGateway.png", "StorageGatewayVirtualTapeLibrary.png", "StorageGatewayVolumeGateway.png"],
}


# ═══════════════════════════════════════════════════════════════════
# Azure: complete icon list from nicolaparo/azure-icons (256px)
# ═══════════════════════════════════════════════════════════════════

AZURE_ALL_ICONS: list[str] = ["icon-abs-member.png","icon-active-directory-connect-health.png","icon-activity-log.png","icon-advisor.png","icon-alerts.png","icon-all-resources.png","icon-analysis-services.png","icon-api-management-services.png","icon-app-registrations.png","icon-app-service-certificates.png","icon-app-service-domains.png","icon-app-service-environments.png","icon-app-service-plans.png","icon-app-services.png","icon-application-gateways.png","icon-application-insights.png","icon-application-security-groups.png","icon-automanaged-vm.png","icon-automation-accounts.png","icon-availability-sets.png","icon-avs.png","icon-azure-active-directory.png","icon-azure-ad-b2c.png","icon-azure-ad-domain-services.png","icon-azure-ad-identity-protection.png","icon-azure-ad-roles-and-administrators.png","icon-azure-api-for-fhir.png","icon-azure-arc.png","icon-azure-backup-center.png","icon-azure-blockchain-service.png","icon-azure-cloud-shell.png","icon-azure-cosmos-db.png","icon-azure-data-catalog.png","icon-azure-data-explorer-clusters.png","icon-azure-database-mariadb-server.png","icon-azure-database-migration-services.png","icon-azure-database-mysql-server.png","icon-azure-database-postgresql-server.png","icon-azure-databricks.png","icon-azure-defender.png","icon-azure-devops.png","icon-azure-firewall-manager.png","icon-azure-hcp-cache.png","icon-azure-lighthouse.png","icon-azure-maps-accounts.png","icon-azure-media-service.png","icon-azure-migrate.png","icon-azure-netapp-files.png","icon-azure-openai.png","icon-azure-sentinel.png","icon-azure-sphere.png","icon-azure-spring-cloud.png","icon-azure-sql-server-stretch-databases.png","icon-azure-sql-vm.png","icon-azure-sql.png","icon-azure-stack-edge.png","icon-azure-stack.png","icon-azure-synapse-analytics.png","icon-azure-token-service.png","icon-azure-workbooks.png","icon-backlog.png","icon-batch-accounts.png","icon-biz-talk.png","icon-blob-block.png","icon-blob-page.png","icon-blueprints.png","icon-bot-services.png","icon-branch.png","icon-browser.png","icon-bug.png","icon-builds.png","icon-cache-redis.png","icon-cache.png","icon-capacity.png","icon-cdn-profiles.png","icon-code.png","icon-cognitive-services.png","icon-commit.png","icon-compliance.png","icon-conditional-access.png","icon-connections.png","icon-consortium.png","icon-container-instances.png","icon-container-registries.png","icon-controls-horizontal.png","icon-controls.png","icon-cost-alerts.png","icon-cost-analysis.png","icon-cost-budgets.png","icon-cost-management-and-billing.png","icon-cost-management.png","icon-counter.png","icon-cplusplus.png","icon-csharp.png","icon-cubes.png","icon-dashboard.png","icon-data-box-edge.png","icon-data-box.png","icon-data-factory.png","icon-data-lake-storage-gen1.png","icon-data-lake-store-gen1.png","icon-data-share-invitations.png","icon-data-shares.png","icon-ddos-protection-plans.png","icon-detonation.png","icon-dev-console.png","icon-device-provisioning-services.png","icon-device-security-apple.png","icon-device-security-google.png","icon-device-security-windows.png","icon-devtest-labs.png","icon-diagnostics-settings.png","icon-digital-twins.png","icon-disk-encryption-sets.png","icon-disks-snapshots.png","icon-disks.png","icon-dns-zones.png","icon-download.png","icon-education.png","icon-elastic-job-agents.png","icon-entra-id.png","icon-enterprise-applications.png","icon-error.png","icon-event-grid-domains.png","icon-event-grid-subscriptions.png","icon-event-grid-topics.png","icon-event-hub-clusters.png","icon-event-hubs.png","icon-expressroute-circuits.png","icon-expressroute-direct.png","icon-extendedsecurityupdates.png","icon-extensions.png","icon-file.png","icon-files.png","icon-firewalls.png","icon-folder-blank.png","icon-folder-website.png","icon-free-services.png","icon-front-doors.png","icon-ftp.png","icon-function-apps.png","icon-gear.png","icon-globe-error.png","icon-globe-success.png","icon-globe-warning.png","icon-globe.png","icon-groups.png","icon-guide.png","icon-hd-insight-clusters.png","icon-heart.png","icon-help-and-support.png","icon-identity-governance.png","icon-image-definitions.png","icon-image-versions.png","icon-image.png","icon-images.png","icon-import-export-jobs.png","icon-information.png","icon-infrastructure-backup.png","icon-input-output.png","icon-instance-pools.png","icon-integration-accounts.png","icon-internet-analyzer-profiles.png","icon-intune-for-education.png","icon-intune.png","icon-iot-central-applications.png","icon-iot-edge.png","icon-iot-hub.png","icon-ip-groups.png","icon-java.png","icon-javascript.png","icon-journey-hub.png","icon-key-vaults.png","icon-kubernetes-services.png","icon-lab-services.png","icon-launch-portal.png","icon-learn.png","icon-load-balancers.png","icon-load-test.png","icon-local-network-gateways.png","icon-location.png","icon-log-analytics-workspaces.png","icon-log-streaming.png","icon-logic-apps.png","icon-machine-learning-studio-web-service-plans.png","icon-machine-learning-studio-workspaces.png","icon-machine-learning.png","icon-machinesazurearc.png","icon-managed-applications-center.png","icon-managed-database.png","icon-managed-identities.png","icon-management-groups.png","icon-management-portal.png","icon-marketplace.png","icon-media-file.png","icon-media.png","icon-mesh-applications.png","icon-metrics.png","icon-microsoft-defender-for-cloud.png","icon-microsoft-sentinel.png","icon-mobile-engagement.png","icon-mobile.png","icon-module.png","icon-monitor.png","icon-multi-tenancy.png","icon-my-customers.png","icon-nat.png","icon-network-interfaces.png","icon-network-security-groups.png","icon-network-watcher.png","icon-notification-hub-namespaces.png","icon-notification-hubs.png","icon-offers.png","icon-outbound-connection.png","icon-partner-topic.png","icon-peering-service.png","icon-php.png","icon-plans.png","icon-policy.png","icon-power-bi-embedded.png","icon-power-up.png","icon-power.png","icon-powershell.png","icon-preview.png","icon-private-endpoints.png","icon-private-link-hub.png","icon-private-link-service.png","icon-private-link.png","icon-process-explorer.png","icon-production-ready-database.png","icon-proximity-placement-groups.png","icon-public-ip-addresses.png","icon-public-ip-prefixes.png","icon-python.png","icon-quickstart-center.png","icon-recent.png","icon-recovery-services-vaults.png","icon-relays.png","icon-remote-rendering.png","icon-reservations.png","icon-resource-explorer.png","icon-resource-graph-explorer.png","icon-resource-group-list.png","icon-resource-groups.png","icon-resource-linked.png","icon-resource-mover.png","icon-route-filters.png","icon-route-tables.png","icon-rtos.png","icon-sap-azure-monitor.png","icon-scale.png","icon-scheduler.png","icon-search-grid.png","icon-search-services.png","icon-search.png","icon-security-center.png","icon-server-farm.png","icon-service-bus.png","icon-service-endpoint-policies.png","icon-service-fabric-clusters.png","icon-service-health.png","icon-service-providers.png","icon-shared-image-galleries.png","icon-signalr.png","icon-software-as-a-service.png","icon-solutions.png","icon-sql-data-warehouses.png","icon-sql-database.png","icon-sql-elastic-pools.png","icon-sql-managed-instance.png","icon-sql-server.png","icon-ssd.png","icon-ssh-keys.png","icon-ssis-lift-and-shift-ir.png","icon-static-apps.png","icon-storage-accounts-classic.png","icon-storage-accounts.png","icon-storage-azure-files.png","icon-storage-container.png","icon-storage-queue.png","icon-storage-sync-services.png","icon-storagemovers.png","icon-storsimple-data-managers.png","icon-storsimple-device-managers.png","icon-stream-analytics-jobs.png","icon-subscriptions.png","icon-system-topic.png","icon-table.png","icon-tag.png","icon-tags.png","icon-template-specs.png","icon-tfs-vc-repository.png","icon-time-series-data-sets.png","icon-time-series-insights-access-policies.png","icon-time-series-insights-environments.png","icon-time-series-insights-event-sources.png","icon-toolbox.png","icon-traffic-manager-profiles.png","icon-translator-text.png","icon-universal-print.png","icon-updates.png","icon-user-privacy.png","icon-user-subscriptions.png","icon-users.png","icon-versions.png","icon-virtual-clusters.png","icon-virtual-machine.png","icon-virtual-network-gateways.png","icon-virtual-networks.png","icon-virtual-wans.png","icon-vm-scale-sets.png","icon-web-environment.png","icon-web-slots.png","icon-web-test.png","icon-website-power.png","icon-website-staging.png","icon-windows-virtual-desktop.png","icon-workbooks.png","icon-workflow.png","icon-workspaces.png"]


# ═══════════════════════════════════════════════════════════════════
# Third-party Icons — from cdn.simpleicons.org (SVG)
# (slug, canonical_id, display_name, category, subcategory, brand_color)
# ═══════════════════════════════════════════════════════════════════

SIMPLE_ICON_ENTRIES: list[tuple[str, str, str, str, str, str]] = [
    # --- Databases ---
    ("oracle", "oracle_db", "Oracle Database", "databases", "relational", "#F80000"),
    ("postgresql", "postgresql", "PostgreSQL", "databases", "relational", "#4169E1"),
    ("mysql", "mysql", "MySQL", "databases", "relational", "#4479A1"),
    ("mariadb", "mariadb", "MariaDB", "databases", "relational", "#003545"),
    ("sqlite", "sqlite", "SQLite", "databases", "relational", "#003B57"),
    ("cockroachlabs", "cockroachdb", "CockroachDB", "databases", "relational", "#6933FF"),
    ("microsoftsqlserver", "sql_server", "SQL Server", "databases", "relational", "#CC2927"),
    ("mongodb", "mongodb", "MongoDB", "databases", "nosql", "#47A248"),
    ("apachecassandra", "cassandra", "Cassandra", "databases", "nosql", "#1287B1"),
    ("couchbase", "couchbase", "Couchbase", "databases", "nosql", "#EA2328"),
    ("redis", "redis", "Redis", "databases", "nosql", "#FF4438"),
    ("neo4j", "neo4j", "Neo4j", "databases", "nosql", "#4581C3"),
    ("elasticsearch", "elasticsearch", "Elasticsearch", "databases", "nosql", "#005571"),
    ("opensearch", "opensearch", "OpenSearch", "databases", "nosql", "#005EB8"),
    ("snowflake", "snowflake", "Snowflake", "databases", "cloud", "#29B5E8"),
    ("databricks", "databricks", "Databricks", "databases", "cloud", "#FF3621"),
    ("googlebigquery", "bigquery", "BigQuery", "databases", "cloud", "#669DF6"),
    ("teradata", "teradata", "Teradata", "databases", "warehouse", "#F37440"),
    # --- Data Engineering ---
    ("apacheairflow", "airflow", "Apache Airflow", "data-engineering", "orchestration", "#017CEE"),
    ("dagster", "dagster", "Dagster", "data-engineering", "orchestration", "#4F43DD"),
    ("prefect", "prefect", "Prefect", "data-engineering", "orchestration", "#024DFD"),
    ("apachespark", "spark", "Apache Spark", "data-engineering", "processing", "#E25A1C"),
    ("apacheflink", "flink", "Apache Flink", "data-engineering", "processing", "#E6526F"),
    ("apachekafka", "kafka", "Apache Kafka", "data-engineering", "streaming", "#231F20"),
    ("confluent", "confluent", "Confluent", "data-engineering", "streaming", "#000000"),
    ("rabbitmq", "rabbitmq", "RabbitMQ", "data-engineering", "streaming", "#FF6600"),
    ("apachepulsar", "pulsar", "Apache Pulsar", "data-engineering", "streaming", "#188FFF"),
    ("dbt", "dbt", "dbt", "data-engineering", "transformation", "#FF694B"),
    ("airbyte", "airbyte", "Airbyte", "data-engineering", "integration", "#615EFF"),
    ("informatica", "informatica", "Informatica", "data-engineering", "integration", "#FF4D00"),
    ("talend", "talend", "Talend", "data-engineering", "integration", "#FF6D70"),
    ("fivetran", "fivetran", "Fivetran", "data-engineering", "integration", "#0073FF"),
    ("mulesoft", "mulesoft", "MuleSoft", "integration", "etl", "#00A1DF"),
    ("flyway", "flyway", "Flyway", "data-engineering", "migration", "#CC0200"),
    ("liquibase", "liquibase", "Liquibase", "data-engineering", "migration", "#2962FF"),
    # --- DevOps ---
    ("github", "github", "GitHub", "devops", "version-control", "#181717"),
    ("gitlab", "gitlab", "GitLab", "devops", "version-control", "#FC6D26"),
    ("bitbucket", "bitbucket", "Bitbucket", "devops", "version-control", "#0052CC"),
    ("git", "git", "Git", "devops", "version-control", "#F05032"),
    ("jenkins", "jenkins", "Jenkins", "devops", "ci-cd", "#D24939"),
    ("circleci", "circleci", "CircleCI", "devops", "ci-cd", "#343434"),
    ("githubactions", "github_actions", "GitHub Actions", "devops", "ci-cd", "#2088FF"),
    ("azurepipelines", "az_pipelines_si", "Azure Pipelines", "devops", "ci-cd", "#2560E0"),
    ("argo", "argocd", "Argo CD", "devops", "ci-cd", "#EF7B4D"),
    ("docker", "docker", "Docker", "devops", "containers", "#2496ED"),
    ("kubernetes", "kubernetes", "Kubernetes", "devops", "containers", "#326CE5"),
    ("helm", "helm", "Helm", "devops", "containers", "#0F1689"),
    ("containerd", "containerd", "containerd", "devops", "containers", "#575757"),
    ("terraform", "terraform", "Terraform", "devops", "iac", "#844FBA"),
    ("pulumi", "pulumi", "Pulumi", "devops", "iac", "#8A3391"),
    ("ansible", "ansible", "Ansible", "devops", "iac", "#EE0000"),
    ("sonarqube", "sonarqube", "SonarQube", "devops", "other", "#4E9BCD"),
    ("vault", "hashicorp_vault", "HashiCorp Vault", "security", "secrets", "#FFEC6E"),
    # --- AI/ML ---
    ("tensorflow", "tensorflow", "TensorFlow", "ai-ml", "", "#FF6F00"),
    ("pytorch", "pytorch", "PyTorch", "ai-ml", "", "#EE4C2C"),
    ("huggingface", "huggingface", "Hugging Face", "ai-ml", "", "#FFD21E"),
    ("openai", "openai", "OpenAI", "ai-ml", "", "#412991"),
    ("mlflow", "mlflow", "MLflow", "ai-ml", "", "#0194E2"),
    ("weightsandbiases", "wandb", "Weights & Biases", "ai-ml", "", "#FFBE00"),
    ("jupyter", "jupyter", "Jupyter", "ai-ml", "", "#F37626"),
    ("scikitlearn", "scikit_learn", "scikit-learn", "ai-ml", "", "#F7931E"),
    ("numpy", "numpy", "NumPy", "ai-ml", "", "#013243"),
    ("pandas", "pandas", "pandas", "ai-ml", "", "#150458"),
    ("keras", "keras", "Keras", "ai-ml", "", "#D00000"),
    ("opencv", "opencv", "OpenCV", "ai-ml", "", "#5C3EE8"),
    # --- Monitoring ---
    ("prometheus", "prometheus", "Prometheus", "monitoring", "", "#E6522C"),
    ("grafana", "grafana", "Grafana", "monitoring", "", "#F46800"),
    ("datadog", "datadog", "Datadog", "monitoring", "", "#632CA6"),
    ("newrelic", "newrelic", "New Relic", "monitoring", "", "#1CE783"),
    ("splunk", "splunk", "Splunk", "monitoring", "", "#000000"),
    ("dynatrace", "dynatrace", "Dynatrace", "monitoring", "", "#1496FF"),
    ("elastic", "elastic", "Elastic", "monitoring", "", "#005571"),
    # --- Security ---
    ("okta", "okta", "Okta", "security", "identity", "#007DC1"),
    ("auth0", "auth0", "Auth0", "security", "identity", "#EB5424"),
    ("snyk", "snyk", "Snyk", "security", "scanning", "#4C4A73"),
    ("crowdstrike", "crowdstrike", "CrowdStrike", "security", "other", "#FF0000"),
    # --- Integration ---
    ("graphql", "graphql", "GraphQL", "integration", "api", "#E10098"),
    ("kong", "kong", "Kong", "integration", "api", "#003459"),
    ("apigee", "apigee", "Apigee", "integration", "api", "#4285F4"),
    # --- Languages / General ---
    ("python", "python_lang", "Python", "general", "", "#3776AB"),
    ("openjdk", "java", "Java", "general", "", "#ED8B00"),
    ("go", "go_lang", "Go", "general", "", "#00ADD8"),
    ("nodedotjs", "nodejs", "Node.js", "general", "", "#5FA04E"),
    ("dotnet", "dotnet", ".NET", "general", "", "#512BD4"),
    ("rust", "rust_lang", "Rust", "general", "", "#000000"),
    ("typescript", "typescript", "TypeScript", "general", "", "#3178C6"),
    # --- Analytics ---
    ("tableau", "tableau", "Tableau", "analytics", "", "#E97627"),
    ("looker", "looker", "Looker", "analytics", "", "#4285F4"),
    ("powerbi", "power_bi_si", "Power BI", "analytics", "", "#F2C811"),
    ("metabase", "metabase", "Metabase", "analytics", "", "#509EE3"),
    ("apache", "apache", "Apache", "general", "", "#D22128"),
    ("googlecloud", "gcp", "Google Cloud", "general", "", "#4285F4"),
]


# ═══════════════════════════════════════════════════════════════════
# Microsoft Fabric
# (id, display_name, subcategory, abbreviation, brand_color)
#
# Real icons come from Microsoft's own @fabric-msft/svg-icons package
# (MIT licensed), published for Fabric platform extension development:
# https://github.com/microsoft/fabric-samples/blob/main/docs-samples/Icons.zip
# See FABRIC_ICON_SOURCE below for the id -> source-icon mapping. Any id
# without a source entry has no matching icon in that package and falls
# back to a text abbreviation.
# ═══════════════════════════════════════════════════════════════════

FABRIC_ENTRIES: list[tuple[str, str, str, str, str]] = [
    ("fabric", "Microsoft Fabric", "platform", "Fab", "#117865"),
    ("fabric_workspace", "Fabric Workspace", "platform", "FW", "#117865"),
    ("fabric_capacity", "Fabric Capacity", "platform", "FC", "#117865"),
    ("fabric_admin", "Fabric Administration", "platform", "FA", "#117865"),
    ("fabric_data_factory", "Data Factory (Fabric)", "data-factory", "DF", "#117865"),
    ("fabric_pipeline", "Data Pipeline", "data-factory", "PL", "#117865"),
    ("fabric_dataflow_gen2", "Dataflow Gen2", "data-factory", "DG", "#117865"),
    ("fabric_onelake", "OneLake", "onelake", "OL", "#117865"),
    ("fabric_onelake_hub", "OneLake Data Hub", "onelake", "OH", "#117865"),
    ("fabric_shortcuts", "Shortcuts", "onelake", "SC", "#117865"),
    ("fabric_lakehouse", "Lakehouse", "lakehouse", "LH", "#117865"),
    ("fabric_delta_tables", "Delta Tables", "lakehouse", "DT", "#117865"),
    ("fabric_warehouse", "Fabric Warehouse", "warehouse", "WH", "#117865"),
    ("fabric_sql_endpoint", "SQL Analytics Endpoint", "warehouse", "SE", "#117865"),
    ("fabric_notebook", "Notebook", "data-engineering", "NB", "#117865"),
    ("fabric_spark_job", "Spark Job Definition", "data-engineering", "SJ", "#117865"),
    ("fabric_environment", "Environment", "data-engineering", "EN", "#117865"),
    ("fabric_data_science", "Data Science", "data-science", "DS", "#117865"),
    ("fabric_experiment", "Experiment", "data-science", "EX", "#117865"),
    ("fabric_ml_model", "ML Model", "data-science", "ML", "#117865"),
    ("fabric_rti", "Real-Time Intelligence", "real-time-intelligence", "RT", "#117865"),
    ("fabric_eventhouse", "Eventhouse", "real-time-intelligence", "EH", "#117865"),
    ("fabric_eventstream", "Eventstream", "real-time-intelligence", "ES", "#117865"),
    ("fabric_kql_database", "KQL Database", "real-time-intelligence", "KQ", "#117865"),
    ("fabric_rt_dashboard", "Real-Time Dashboard", "real-time-intelligence", "RD", "#117865"),
    ("fabric_rt_hub", "Real-Time Hub", "real-time-intelligence", "RH", "#117865"),
    ("fabric_power_bi", "Power BI", "power-bi", "PBI", "#F2C811"),
    ("fabric_semantic_model", "Semantic Model", "power-bi", "SM", "#F2C811"),
    ("fabric_report", "Report", "power-bi", "RP", "#F2C811"),
    ("fabric_dashboard", "Dashboard", "power-bi", "DB", "#F2C811"),
    ("fabric_paginated_report", "Paginated Report", "power-bi", "PR", "#F2C811"),
    ("fabric_data_mart", "Data Mart", "power-bi", "DM", "#F2C811"),
    ("fabric_direct_lake", "Direct Lake", "general", "DL", "#117865"),
    ("fabric_mirroring", "Mirroring", "general", "MR", "#117865"),
    ("fabric_mirrored_db", "Mirrored Database", "general", "MD", "#117865"),
    ("fabric_purview", "Purview Integration", "governance", "PV", "#117865"),
    ("fabric_governance", "Governance", "governance", "GV", "#117865"),
    ("fabric_lineage", "Data Lineage", "governance", "LN", "#117865"),
]

FABRIC_ICONS_ZIP = "https://raw.githubusercontent.com/microsoft/fabric-samples/main/docs-samples/Icons.zip"

# FABRIC_ENTRIES id -> exact icon name (without size/style suffix) in the
# @fabric-msft/svg-icons package. Preferred size/style is picked at
# download time (color > item > filled > regular, largest usable size).
# Ids not listed here have no matching icon in the package.
FABRIC_ICON_SOURCE: dict[str, str] = {
    "fabric": "fabric",
    "fabric_workspace": "group_workspace",
    "fabric_capacity": "fabric",
    "fabric_admin": "fabric",
    "fabric_data_factory": "data_factory",
    "fabric_pipeline": "pipeline",
    "fabric_dataflow_gen2": "dataflow",
    "fabric_onelake": "one_lake",
    "fabric_onelake_hub": "one_lake",
    "fabric_lakehouse": "lakehouse",
    "fabric_warehouse": "data_warehouse",
    "fabric_sql_endpoint": "cloud_endpoint",
    "fabric_notebook": "notebook",
    "fabric_spark_job": "notebook_code",
    "fabric_environment": "environment",
    "fabric_data_science": "data_science",
    "fabric_experiment": "experiments",
    "fabric_ml_model": "model",
    "fabric_rti": "real_time_intelligence",
    "fabric_eventhouse": "event_house",
    "fabric_eventstream": "eventstream",
    "fabric_kql_database": "database_kql",
    "fabric_rt_dashboard": "real_time_dashboard",
    "fabric_power_bi": "power_bi",
    "fabric_semantic_model": "semantic_model",
    "fabric_report": "report",
    "fabric_dashboard": "dashboard",
    "fabric_paginated_report": "paginated_report",
    "fabric_data_mart": "data_warehouse",
    "fabric_direct_lake": "lakehouse",
    "fabric_mirroring": "mirrored_generic_database",
    "fabric_mirrored_db": "mirrored_generic_database",
    "fabric_purview": "purview",
    "fabric_governance": "purview",
    "fabric_lineage": "runtime_lineage",
    # Not in the package: fabric_shortcuts, fabric_delta_tables, fabric_rt_hub
}

# Extra real-world phrasings, on top of each entry's own display_name.
FABRIC_EXTRA_ALIASES: dict[str, list[str]] = {
    "fabric_warehouse": ["Fabric Data Warehouse", "Data Warehouse (Fabric)", "Gold Layer"],
    "fabric_lakehouse": ["Bronze Layer", "Silver Layer"],
    "fabric_data_factory": ["Azure Data Factory (Fabric)", "ADF (Fabric)"],
    "fabric_power_bi": ["PowerBI"],
    "fabric_kql_database": ["KQL DB"],
    "fabric_eventhouse": ["Event House"],
}

_FABRIC_STYLE_PRIORITY = ["color", "item", "filled", "regular", "non-item"]
_FABRIC_SIZE_PRIORITY = [32, 24, 40, 20, 48, 28, 16, 64]


def download_fabric_icons() -> tuple[int, int]:
    """Fetch Microsoft's official Fabric icon package and copy the icons
    FABRIC_ICON_SOURCE maps to into assets/icons/microsoft/fabric/."""
    import io
    import shutil
    import tempfile
    import zipfile

    print("\n" + "=" * 60)
    print("DOWNLOADING MICROSOFT FABRIC ICONS")
    print("=" * 60)

    data = _download(FABRIC_ICONS_ZIP)
    if not data:
        print("  ✗ could not download Icons.zip")
        return 0, len(FABRIC_ICON_SOURCE)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            zf.extractall(tmp_path)

        svg_dirs = list(tmp_path.glob("**/dist/svg"))
        if not svg_dirs:
            print("  ✗ unexpected package layout — no dist/svg/ found")
            return 0, len(FABRIC_ICON_SOURCE)
        svg_dir = svg_dirs[0]
        png_dir = svg_dir.parent / "png"
        available = {f.stem for f in svg_dir.glob("*.svg")}

        by_id = {eid: (subcat) for eid, _, subcat, _, _ in FABRIC_ENTRIES}
        ok = fail = 0
        for eid, base_name in FABRIC_ICON_SOURCE.items():
            subcat = by_id.get(eid, "general")
            match = None
            for size in _FABRIC_SIZE_PRIORITY:
                for style in _FABRIC_STYLE_PRIORITY:
                    candidate = f"{base_name}_{size}_{style}"
                    if candidate in available:
                        match = candidate
                        break
                if match:
                    break

            if not match:
                print(f"  ✗ {eid} (no source match for '{base_name}')")
                fail += 1
                continue

            dest_dir = ASSETS_DIR / "microsoft" / "fabric" / subcat
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy(svg_dir / f"{match}.svg", dest_dir / f"{eid}.svg")
            png_src = png_dir / f"{match}.png"
            if png_src.exists():
                shutil.copy(png_src, dest_dir / f"{eid}.png")
            print(f"  ✓ {eid} <- {match}")
            ok += 1

    print(f"\n  Fabric: {ok} OK, {fail} failed")
    return ok, fail


# ═══════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════

def _download(url: str, timeout: int = 20) -> bytes | None:
    try:
        req = Request(url, headers={"User-Agent": "XebiaProposalStudio/1.0"})
        with urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                data = resp.read()
                if len(data) > 100:
                    return data
    except (URLError, HTTPError, OSError):
        pass
    return None


def _ensure_square_png(path: Path, size: int = 128):
    if not HAS_PILLOW:
        return
    try:
        img = Image.open(path)
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        w, h = img.size
        mx = max(w, h)
        if w != h:
            sq = Image.new("RGBA", (mx, mx), (0, 0, 0, 0))
            sq.paste(img, ((mx - w) // 2, (mx - h) // 2))
            img = sq
        if img.size[0] != size:
            img = img.resize((size, size), Image.LANCZOS)
        img.save(path, "PNG")
    except Exception:
        pass


def _filename_to_id(filename: str) -> str:
    name = filename.replace(".png", "")
    name = re.sub(r"_Dark$", "_dark", name)
    parts = re.findall(r"[A-Z][a-z0-9]*|[A-Z]+(?=[A-Z]|$)|[a-z0-9]+", name)
    return "_".join(p.lower() for p in parts) if parts else name.lower()


def _azure_filename_to_id(filename: str) -> str:
    name = filename.replace(".png", "").replace("icon-", "")
    return name.replace("-", "_")


def _display_name_from_id(eid: str) -> str:
    parts = eid.replace("_", " ").split()
    return " ".join(w.capitalize() if len(w) > 2 else w.upper() for w in parts)


# ═══════════════════════════════════════════════════════════════════
# AWS category → local directory mapping
# ═══════════════════════════════════════════════════════════════════

AWS_CAT_DIR = {
    "Analytics": "analytics",
    "ApplicationIntegration": "app-integration",
    "ArtificialIntelligence": "ai-ml",
    "Blockchain": "general",
    "BusinessApplications": "business-apps",
    "CloudFinancialManagement": "management",
    "Compute": "compute",
    "Containers": "containers",
    "CustomerEnablement": "general",
    "CustomerExperience": "general",
    "Database": "database",
    "DeveloperTools": "developer-tools",
    "EndUserComputing": "end-user-computing",
    "FrontEndWebMobile": "general",
    "Games": "general",
    "General": "general",
    "Groups": "general",
    "InternetOfThings": "iot",
    "ManagementGovernance": "management",
    "MediaServices": "media",
    "MigrationModernization": "migration",
    "MulticloudandHybrid": "general",
    "NetworkingContentDelivery": "networking",
    "QuantumTechnologies": "general",
    "Satellite": "general",
    "SecurityIdentityCompliance": "security-identity",
    "Serverless": "compute",
    "Storage": "storage",
}


# ═══════════════════════════════════════════════════════════════════
# Download functions
# ═══════════════════════════════════════════════════════════════════

def download_aws(size: int = 128) -> tuple[int, int]:
    print("\n" + "=" * 60)
    print("DOWNLOADING AWS ICONS (complete official collection)")
    print("=" * 60)
    ok = fail = 0
    for cat, filenames in AWS_CATEGORIES.items():
        subdir = AWS_CAT_DIR.get(cat, "general")
        dest = ASSETS_DIR / "cloud" / "aws" / subdir
        dest.mkdir(parents=True, exist_ok=True)
        print(f"\n  {cat} ({len(filenames)} icons)")
        for fn in filenames:
            eid = f"aws_{_filename_to_id(fn)}"
            out = dest / f"{eid}.png"
            if out.exists() and out.stat().st_size > 100:
                ok += 1
                continue
            url = f"{AWS_BASE}/{cat}/{fn}"
            data = _download(url)
            if data:
                out.write_bytes(data)
                _ensure_square_png(out, size)
                ok += 1
            else:
                print(f"    ✗ {fn}")
                fail += 1
    print(f"\n  AWS: {ok} OK, {fail} failed")
    return ok, fail


def download_azure(size: int = 128) -> tuple[int, int]:
    print("\n" + "=" * 60)
    print("DOWNLOADING AZURE ICONS (complete official collection)")
    print("=" * 60)
    ok = fail = 0
    dest = ASSETS_DIR / "cloud" / "azure" / "all"
    dest.mkdir(parents=True, exist_ok=True)
    for fn in AZURE_ALL_ICONS:
        eid = f"az_{_azure_filename_to_id(fn)}"
        out = dest / f"{eid}.png"
        if out.exists() and out.stat().st_size > 100:
            ok += 1
            continue
        url = f"{AZURE_BASE}/{fn}"
        data = _download(url)
        if data:
            out.write_bytes(data)
            _ensure_square_png(out, size)
            ok += 1
        else:
            print(f"    ✗ {fn}")
            fail += 1
    print(f"\n  Azure: {ok} OK, {fail} failed of {len(AZURE_ALL_ICONS)}")
    return ok, fail


def download_thirdparty(size: int = 128) -> tuple[int, int]:
    print("\n" + "=" * 60)
    print("DOWNLOADING THIRD-PARTY ICONS (simple-icons)")
    print("=" * 60)
    ok = fail = 0
    for slug, cid, display, cat, subcat, color in SIMPLE_ICON_ENTRIES:
        parts = cat.split("/")
        dest = ASSETS_DIR / Path(*parts) / subcat if subcat else ASSETS_DIR / Path(*parts)
        dest.mkdir(parents=True, exist_ok=True)
        out_svg = dest / f"{cid}.svg"
        out_png = dest / f"{cid}.png"
        if (out_svg.exists() and out_svg.stat().st_size > 100) or \
           (out_png.exists() and out_png.stat().st_size > 100):
            ok += 1
            continue
        data = _download(f"{SIMPLE_ICONS}/{slug}")
        if not data:
            # Primary CDN blocked/unreachable — same open-source icon set
            # is also mirrored on GitHub.
            data = _download(f"{SIMPLE_ICONS_GITHUB_MIRROR}/{slug}.svg")

        if not data:
            print(f"  ✗ {cid} ({slug})")
            fail += 1
            continue

        out_svg.write_bytes(data)
        if HAS_CAIROSVG:
            try:
                cairosvg.svg2png(bytestring=data, write_to=str(out_png),
                                  output_width=size, output_height=size,
                                  background_color="white")
            except Exception:
                pass
        print(f"  ✓ {cid}")
        ok += 1
    print(f"\n  Third-party: {ok} OK, {fail} failed")
    return ok, fail


def download_pbi(size: int = 128) -> tuple[int, int]:
    print("\n" + "=" * 60)
    print("DOWNLOADING POWER BI ICONS")
    print("=" * 60)
    dest = ASSETS_DIR / "microsoft" / "power-bi"
    dest.mkdir(parents=True, exist_ok=True)
    out = dest / "power_bi.png"
    if out.exists() and out.stat().st_size > 100:
        print("  power_bi: already exists")
        return 1, 0
    url = f"{PBI_BASE}/Power-BI.png"
    data = _download(url)
    if data:
        out.write_bytes(data)
        _ensure_square_png(out, size)
        print("  ✓ power_bi")
        return 1, 0
    print("  ✗ power_bi")
    return 0, 1


# ═══════════════════════════════════════════════════════════════════
# Registry builder
# ═══════════════════════════════════════════════════════════════════

def build_registry():
    print("\n" + "=" * 60)
    print("BUILDING REGISTRY")
    print("=" * 60)
    entries: list[dict] = []
    seen: set[str] = set()

    def _add(entry: dict):
        eid = entry["id"]
        if eid not in seen:
            seen.add(eid)
            entries.append(entry)

    for cat, filenames in AWS_CATEGORIES.items():
        subdir = AWS_CAT_DIR.get(cat, "general")
        for fn in filenames:
            eid = f"aws_{_filename_to_id(fn)}"
            rel = f"cloud/aws/{subdir}/{eid}.png"
            display = fn.replace(".png", "")
            aliases = [display]
            short = display.replace("AmazonS3", "S3").replace("Amazon", "").replace("AWS", "").strip()
            if short and short != display:
                aliases.append(short)
            _add({
                "id": eid,
                "technology": display,
                "display_name": display,
                "vendor": "AWS",
                "platform": "aws",
                "category": f"cloud/aws",
                "subcategory": cat,
                "service_type": "cloud",
                "aliases": aliases,
                "keywords": [cat.lower()],
                "abbreviation": eid.replace("aws_", "")[:4].upper(),
                "brand_color": "#FF9900",
                "file_path": rel,
                "png_path": rel,
                "official_source": f"{AWS_BASE}/{cat}/{fn}",
                "official_asset": True,
                "last_verified": "2026-08-20",
            })

    for fn in AZURE_ALL_ICONS:
        eid = f"az_{_azure_filename_to_id(fn)}"
        rel = f"cloud/azure/all/{eid}.png"
        display = fn.replace(".png", "").replace("icon-", "").replace("-", " ").title()
        aliases = [display, display.replace(" ", "")]
        _add({
            "id": eid,
            "technology": display,
            "display_name": display,
            "vendor": "Microsoft",
            "platform": "azure",
            "category": "cloud/azure",
            "subcategory": "",
            "service_type": "cloud",
            "aliases": aliases,
            "keywords": ["azure"],
            "abbreviation": eid.replace("az_", "")[:4].upper(),
            "brand_color": "#0078D4",
            "file_path": rel,
            "png_path": rel,
            "official_source": f"{AZURE_BASE}/{fn}",
            "official_asset": True,
            "last_verified": "2026-08-20",
        })

    for slug, cid, display, cat, subcat, color in SIMPLE_ICON_ENTRIES:
        parts = cat.split("/")
        rel_dir = "/".join(parts + [subcat]) if subcat else "/".join(parts)
        svg_rel = f"{rel_dir}/{cid}.svg"
        png_rel = f"{rel_dir}/{cid}.png"
        has_png = (ASSETS_DIR / png_rel).exists()
        entry = {
            "id": cid,
            "technology": display,
            "display_name": display,
            "vendor": "",
            "platform": "",
            "category": cat,
            "subcategory": subcat,
            "service_type": "tool",
            "aliases": [display],
            "keywords": [subcat or cat],
            "abbreviation": cid[:4].upper(),
            "brand_color": color,
            "file_path": png_rel if has_png else svg_rel,
            "svg_path": svg_rel,
            "official_source": f"{SIMPLE_ICONS}/{slug}",
            "official_asset": False,
            "last_verified": "2026-08-20",
        }
        if has_png:
            entry["png_path"] = png_rel
        _add(entry)

    for eid, display, subcat, abbr, color in FABRIC_ENTRIES:
        rel = f"microsoft/fabric/{subcat}/{eid}.png"
        _add({
            "id": eid,
            "technology": display,
            "display_name": display,
            "vendor": "Microsoft",
            "platform": "fabric",
            "category": "microsoft/fabric",
            "subcategory": subcat,
            "service_type": "cloud",
            "aliases": [display] + FABRIC_EXTRA_ALIASES.get(eid, []),
            "keywords": ["fabric", subcat],
            "abbreviation": abbr,
            "brand_color": color,
            "file_path": rel,
            "png_path": rel,
            "official_source": "",
            "official_asset": False,
            "last_verified": "2026-08-20",
        })

    # Power BI standalone
    _add({
        "id": "power_bi",
        "technology": "Power BI",
        "display_name": "Power BI",
        "vendor": "Microsoft",
        "platform": "microsoft",
        "category": "microsoft/power-bi",
        "subcategory": "",
        "service_type": "tool",
        "aliases": ["Power BI", "PowerBI", "PBI"],
        "keywords": ["analytics", "bi"],
        "abbreviation": "PBI",
        "brand_color": "#F2C811",
        "file_path": "microsoft/power-bi/power_bi.png",
        "png_path": "microsoft/power-bi/power_bi.png",
        "official_source": f"{PBI_BASE}/Power-BI.png",
        "official_asset": True,
        "last_verified": "2026-08-20",
    })

    registry = {
        "version": "1.0.0",
        "description": "Xebia Proposal Studio — Technology Icon Registry",
        "last_updated": "2026-08-20",
        "total_icons": len(entries),
        "icons": entries,
    }
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Registry: {REGISTRY_PATH}")
    print(f"  Entries: {len(entries)}")
    return entries


# ═══════════════════════════════════════════════════════════════════
# Validation
# ═══════════════════════════════════════════════════════════════════

def validate():
    print("\n" + "=" * 60)
    print("VALIDATION REPORT")
    print("=" * 60)
    if not REGISTRY_PATH.exists():
        print("  ERROR: registry.json not found")
        return

    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    icons = data.get("icons", [])
    stats = {"total": len(icons), "present": 0, "missing": 0, "broken": 0, "low_res": 0}
    issues: list[str] = []
    seen_ids: set[str] = set()

    for entry in icons:
        eid = entry.get("id", "")
        if eid in seen_ids:
            issues.append(f"DUPLICATE ID: {eid}")
        seen_ids.add(eid)

        found = False
        for key in ("png_path", "svg_path", "file_path"):
            rel = entry.get(key, "")
            if rel:
                full = ASSETS_DIR / rel
                if full.exists():
                    sz = full.stat().st_size
                    if sz < 100:
                        stats["broken"] += 1
                        issues.append(f"BROKEN: {rel} ({sz}b)")
                    else:
                        found = True
                    break

        if found:
            stats["present"] += 1
        else:
            stats["missing"] += 1

    # Find orphans
    registered = set()
    for entry in icons:
        for key in ("png_path", "svg_path", "file_path"):
            p = entry.get(key, "")
            if p:
                registered.add(p.replace("\\", "/"))

    orphans = []
    for f in ASSETS_DIR.rglob("*"):
        if f.is_file() and f.suffix.lower() in (".png", ".svg", ".jpg") and f.name != "registry.json":
            rel = f.relative_to(ASSETS_DIR).as_posix()
            if rel not in registered:
                orphans.append(rel)

    cov = round(stats["present"] / stats["total"] * 100, 1) if stats["total"] else 0
    print(f"\n  Registered:    {stats['total']}")
    print(f"  Present:       {stats['present']}")
    print(f"  Missing:       {stats['missing']}")
    print(f"  Broken:        {stats['broken']}")
    print(f"  Orphan files:  {len(orphans)}")
    print(f"  COVERAGE:      {cov}%")

    if issues[:20]:
        print(f"\n  Issues ({len(issues)}):")
        for i in issues[:20]:
            print(f"    - {i}")


# ═══════════════════════════════════════════════════════════════════
# Completeness report
# ═══════════════════════════════════════════════════════════════════

def completeness_report():
    print("\n" + "=" * 60)
    print("TECHNOLOGY ICON LIBRARY — COMPLETENESS REPORT")
    print("=" * 60)
    if not REGISTRY_PATH.exists():
        print("  Registry not found")
        return

    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    icons = data.get("icons", [])

    cats: dict[str, dict] = {}
    for entry in icons:
        cat = entry.get("category", "other")
        if cat not in cats:
            cats[cat] = {"total": 0, "avail": 0}
        cats[cat]["total"] += 1
        found = False
        for key in ("png_path", "svg_path", "file_path"):
            rel = entry.get(key, "")
            if rel and (ASSETS_DIR / rel).exists():
                found = True
                break
        if found:
            cats[cat]["avail"] += 1

    total = sum(c["total"] for c in cats.values())
    avail = sum(c["avail"] for c in cats.values())
    pct = round(avail / total * 100, 1) if total else 0
    print(f"\n  Overall: {avail}/{total} icons ({pct}%)\n")

    for cat in sorted(cats.keys()):
        c = cats[cat]
        p = round(c["avail"] / c["total"] * 100) if c["total"] else 0
        bar = "█" * (p // 5) + "░" * (20 - p // 5)
        print(f"  {cat:35s}  {bar}  {p:3d}%  ({c['avail']}/{c['total']})")


# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Build the technology icon library")
    parser.add_argument("--category", choices=["aws", "azure", "thirdparty", "pbi", "fabric"])
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--registry-only", action="store_true")
    parser.add_argument("--size", type=int, default=128)
    args = parser.parse_args()

    if args.report:
        completeness_report()
        return
    if args.validate:
        validate()
        return
    if args.registry_only:
        build_registry()
        completeness_report()
        return

    start = time.time()
    total_ok = total_fail = 0

    cats = [args.category] if args.category else ["aws", "azure", "thirdparty", "pbi", "fabric"]
    for cat in cats:
        if cat == "aws":
            ok, fail = download_aws(args.size)
        elif cat == "azure":
            ok, fail = download_azure(args.size)
        elif cat == "thirdparty":
            ok, fail = download_thirdparty(args.size)
        elif cat == "pbi":
            ok, fail = download_pbi(args.size)
        elif cat == "fabric":
            ok, fail = download_fabric_icons()
        else:
            continue
        total_ok += ok
        total_fail += fail

    build_registry()
    elapsed = time.time() - start
    print(f"\n{'=' * 60}")
    print(f"COMPLETE — {total_ok} downloaded, {total_fail} failed ({elapsed:.1f}s)")
    print(f"{'=' * 60}")
    completeness_report()


if __name__ == "__main__":
    main()
