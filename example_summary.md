# Release Notes

## OpenShift Workloads
## OpenShift Workloads Updates

**Kubernetes Upgrade:** OpenShift Workloads has been upgraded to Kubernetes v1.31.3. This upgrade brings several improvements and new features from the upstream Kubernetes project.

## Subscription Watch
## Subscription Watch Updates

**Improved Metering for MOA Hosted Control Plane (Swatch-3413):**  A new recording rule (`acm_capacity_effective_cpu_cores:sum`) was added to accurately calculate and meter usage based on the total worker node CPU cores associated with a hub cluster. This ensures the correct billing information is linked to the hub cluster's account.

## OpenShift Storage
## OpenShift Storage Update Summary

This release includes several updates to storage components, drivers, and features.

**CNS Volume Migration:**

* The `cns-migration` CLI tool has been removed.  CNS volume migration is now supported and documented through the native vCenter UI for vCenter Server 7.0 Update 3o or later, and vCenter Server 8.0 Update 2 or later. This allows users to migrate volumes between datastores, addressing issues with space limitations and performance.  Attached and detached volumes, as well as special cases like RWX, zonal, and encrypted volumes, are supported.

**CSI Drivers:**

* Several CSI drivers have been updated to their latest upstream releases, including:
    * `aws-ebs-csi-driver`:  Includes breaking changes to metrics names.  Requires updates to the driver's IAM policy.
    * `azure-disk-csi-driver`
    * `gcp-pd-csi-driver`
    * `ibm-vpc-block-csi-driver`: Includes support for cross-account snapshot restore.  Requires using the latest manifests for compatibility.
    * `smb-csi-driver`: Corrected driver test manifest.
* All CSI sidecar containers (`external-attacher`, `external-provisioner`, `external-resizer`, `external-snapshotter`, `node-driver-registrar`, `livenessprobe`) have been updated to their latest upstream versions.

**CSI Snapshot Webhook Removal:**

* The `csi-snapshot-validation-webhook` image and all its references have been removed, aligning with upstream changes.

**Libraries and Dependencies:**

* All OCP and Kubernetes libraries in storage operators have been updated to the versions appropriate for this OCP release. This includes updates to `client-go`, `controller-runtime`, `library-go`, `openshift/api`, `openshift/client-go`, and `operator-sdk`.

**Operator Lifecycle Manager (OLM) Metadata:**

* The OCP release number in the OLM metadata manifests has been updated for the following operators:
    * `local-storage-operator`
    * `aws-efs-csi-driver-operator`
    * `gcp-filestore-csi-driver-operator`
    * `secrets-store-csi-driver-operator`
    * `smb-csi-driver-operator`

**Security Enhancements:**

* `readOnlyRootFilesystem` has been explicitly set to `true` where applicable for enhanced security in several operators, following security best practices.

**Shared Resource CSI Driver Removal:**

* The Shared Resource CSI Driver tech preview feature has been removed. This functionality is now provided through the Builds for OpenShift layered product.

**Tech Preview Features:**

* **Volume Group Snapshots:** Promoted to generally available (GA). This feature allows grouping multiple persistent volumes (PVs) and creating consistent snapshots of them.
* **VolumeAttributesClass:** This feature is now available as a tech preview. It allows specifying additional attributes for volumes, enabling finer-grained control over storage provisioning.  Enabled for `aws-ebs` (resizer and provisioner) and `gcp-pd` drivers.
* **SELinux Contexts for Mounts:**  SELinux context mounts for RWO/RWX persistent volumes are now available as a developer preview.  The `selinux-warning-controller` is now running to provide metrics and events about SELinux usage of PVs.
* **Configurable `maxAllowedBlockVolumesPerNode` for vSphere:** This tech preview feature allows configuring the maximum number of block volumes per node for vSphere environments, supporting the increased limit in vSphere 8.  This feature is currently limited to homogeneous vSphere 8 environments.  The value is configurable up to 255.

## OpenShift Container Platform (OCP) Strategy

**Storage & Virtualization:**

* **CNS Volume Migration (GA):** Migrate vSphere CNS volumes (vSphere CSI volumes) between datastores via the vSphere UI in vSphere 8.0.2 and 7.0 Update 3o. Supports attached/detached, RWX, zonal, and encrypted volumes.  Limited to one volume at a time. See VMware documentation for details.
* **Volume Group Snapshots (GA):** Create consistent snapshots of applications using multiple Persistent Volumes (PVs) for backup and disaster recovery. Supported by CSI drivers shipped with OpenShift Container Platform (OCP).
* **vSphere MachineSets Multi-Disk Support:** Define vSphere machines with multiple disks for flexible storage configurations.
* **vSphere Host Group Mapping for OpenShift Zones (Tech Preview):** Control node placement in vSphere stretched clusters and multi-site scenarios during and after installation.
* **Automatic PV/PVC Deletion on vSphere Cluster Destroy:** Reclaims storage and prevents orphaned resources when destroying vSphere clusters.

**OpenShift Platform & Upgrades:**

* **Upgrade Status Monitoring:** Use `oc adm upgrade status` to track OpenShift cluster upgrade progress.
* **OLM v1 Enhancements:** Supports `OwnNamespace` and `SingleNamespace` install modes for Operators in registry+v1 bundles, simplifies service account creation with least privilege RBAC, and provides a unified catalog for managing operators, Helm charts, and other Kubernetes extensions using the `ClusterExtension` API.
* **All Developer UI Pages in Admin Perspective:** Consolidated developer tools within the Admin Perspective.
* **BYOPKI Image Verification (OCP 4.20):** Use your own public keys to verify container images.
* **AWS MAPI to CAPI Migration:** Seamless transition to Cluster API for AWS infrastructure management.
* **CAPI for Standalone OpenShift Clusters:** Manage standalone clusters (initial focus on load balancers for control plane machines on AWS, Azure, and GCP).  Existing MAPI functionality remains unaffected.
* **Control Plane Machine Set (CPMS) Custom Name Prefixes:** Use the `machineNamePrefix` field in the CPMS CR to customize machine names. Updates trigger a rollout.
* **Cert-manager Support:** Automates certificate management for all configured routes.
* **Gateway API Support (Istio):**  Manage cluster ingress with the standard Gateway API, replacing the older Ingress API.
* **Disconnected Cluster Updates/Booting for Bare Metal (Tech Preview):** Update and boot single/multi-node bare metal clusters without network connectivity.
* **Automatic Boot Image Updates (GCP/AWS):**  OCP 4 clusters on GCP and AWS automatically update boot images to the latest compatible version.
* **Hardware-based LUKS Encryption for IBM Z:** Secure root volume encryption using IBM hardware HSM.
* **On-Cluster Layering (OCL) Enhancements:** Supports disconnected, single-node, two-node, hosted control plane, and multi-architecture OpenShift clusters.  Adds support for node disruption policies and extensions.
* **Image Mode for OpenShift on RHCOS:** Customize RHCOS images directly within the cluster.
* **ROSA HCP AutoNode Developer Preview (Karpenter 1.x, AWS):** Automated node management using Karpenter, replacing the Cluster Autoscaler. Opt-in via OCM and ROSA Cluster APIs.
* **Pre-Upgrade Checks (Tech Preview):** New `oc` command for early detection of potential OpenShift upgrade issues.
* **Sigstore Image Signature Verification:** Enhanced cluster update debugging.
* **Cinder CSI Driver Topology Awareness:** Automated topology-aware volume provisioning.
* **OLMv1 Tech Preview Feature Set:** Enable experimental features via the `TechPreviewNoUpgrade` feature set.
* **Cgroup v1 Removal:** OpenShift 4.19 requires Cgroup v2.
* **User Namespaces (4.20):** Dedicated namespaces for each user's projects and applications.
* **Sigstore API (GA):** Define and enforce image signing and verification policies.
* **Azure Dxv6 and Dsv6 Machine Series Support:** Expanded machine series options in Azure.
* **MultiNetworkPolicy Port Range Support:** Specify port ranges in MultiNetworkPolicy.

**Networking & Infrastructure:**

* **OVN-Kubernetes BGP Routing:** Automates route management between cluster and provider networks.
* **OpenShift Console PatternFly 6 Upgrade:** Refreshed UI for the console and Dynamic Plugin Framework.
* **Nodepool High Availability Improvements:** Topology spread constraints and the de-scheduler improve VM uptime.
* **`oc-mirror v2`:** Rewritten with speed and robustness improvements, including caching and enhanced air-gapped/enclave support.  Supports Cosign tag-based discovery and mirroring.
* **`readOnlyRootFilesystem` for OpenShift Components:** Enhanced container security.
* **ROSA-HCP AutoNode Tech Preview (Karpenter, AWS):** Automated node provisioning and scaling.
* **Simplified OVE Installation:** UI-driven installation process for OpenShift Virtualization Engine.
* **vSphere Multi-NIC and Subnet Support:** Configure VMs with multiple network interfaces and subnets during installation.
* **Hosted Control Plane Pod Labels for Azure Security:**  Improved security compliance in Azure.
* **Reduced Azure Installer Permissions:** Improved security for OpenShift deployments on Azure.
* **GCP Private Google Access Support:** Private and restricted access to Google APIs.
* **Ingress Controller Subnet Specification:** Deploy Load Balancers to specific subnets.
* **Azure Stack Hub IPI Installer Update:** Removed Terraform dependency.
* **Simplified `openshift-installer` Build:** Removed ARO build flag.
* **ARO Boot Diagnostics Option:** Enable boot diagnostics during ARO cluster creation.
* **Cluster API-Based Installer Improvements (4.16+):** Enhanced stability and performance.


## OpenShift Specialist Platform Team
## OpenShift Specialist Platform Team Updates

This document summarizes recent updates from the OpenShift Specialist Platform Team, focusing on user-facing changes.

**vSphere Enhancements & Cleanup:**

* **Multi-Disk Support (SPLAT-1880, SPLAT-2000, SPLAT-1808, SPLAT-1817, SPLAT-1811):**  The installer now supports configuring additional data disks for both control plane and compute nodes on vSphere. This allows greater flexibility for OS and application storage needs.  A new `provisioningMode` flag allows administrators to specify the provisioning type (thin or thick) for these data disks.  The CPMS and Machine API operators have been updated to support these new configurations. Modifying existing data disk definitions on running machines is blocked to prevent unexpected behavior.
* **Host/VM Group Zonal Support (SPLAT-1728, SPLAT-1742, SPLAT-1800, SPLAT-1799, SPLAT-1743):** OpenShift zones can now be mapped to vSphere host groups, enabling deployments on stretched clusters or using a cluster as a region and hosts as zones.  The installer, Machine API Operator (MAO), and Control Plane Machine Set (CPMS) operator have been updated to support this functionality.  Install-config validation now includes checks for tag naming, tag existence, and host group existence.  The Machine API now includes fields for `RegionType`, `ZoneType`, and `VSphereFailureDomainAffinity` to support this feature.  A new feature gate, `VSphereHostVMGroupZonal`, has been added.  The vSphere problem detector (vpd) now includes checks for host groups, VM groups, and host-VM group rules.
* **Feature Gate Cleanup (SPLAT-2079, SPLAT-2078, SPLAT-2072):**  Feature gates for vSphere Control Plane Machine Sets, Static IPs, and Multi vCenter support have been removed following their GA releases. This simplifies the codebase and removes the need for feature gate checks.
* **CNS Volume Cleanup on Destroy (SPLAT-1993, SPLAT-1995):** The installer now checks for and removes lingering CNS volumes upon cluster destroy to prevent wasted disk space and vCenter alerts.  A warning message is displayed to confirm the deletion.

**Networking:**

* **Multi-NIC Support GA (SPLAT-1944, SPLAT-2051):**  vSphere multi-NIC VM creation support is now Generally Available.

**Cloud Provider Removal:**

* **Alibaba Cloud Removal (SPLAT-1454, SPLAT-1722):** Support for Alibaba Cloud has been removed from the cluster-ingress-operator, api, and library-go components.

## Observability UI
## Observability UI Updates

This release focuses on migrating the monitoring plugin to Patternfly 6 to ensure compatibility with OpenShift 4.19 and provide a consistent user experience.

**Monitoring Plugin:**

* The monitoring plugin has been updated to use Patternfly 6, aligning its appearance with the OpenShift 4.19 console.  This ensures a seamless and modern user experience.  Custom classes have been removed where possible to simplify future upgrades.

## OpenShift Over the Air
## OpenShift Over the Air Updates Summary

This release includes several improvements to the update status reporting and configuration of the Cluster Version Operator (CVO).

**Improved Update Status Reporting:**

* **Node Update Status:** The update status now includes detailed information for each node in the cluster, similar to the output of `oc adm upgrade status`. This includes the node's assessment (e.g., Degraded, Unavailable), phase (e.g., Draining, Updating, Rebooting), target OCP version, and any relevant messages.  This information is maintained by a new controller within the Update Status Controller (USC).
* **Health Insight Lifecycle:** The lifecycle management of health insights has been improved.  Health insights are now tied to specific annotations on the ClusterVersion resource, allowing for more reliable reporting and testing.  The USC now acts as a full-reconciliation controller for these insights, ensuring they accurately reflect the cluster's health even after controller restarts or API disruptions.  Artificial health insights can be triggered for testing purposes using annotations on the ClusterVersion resource.
* **Multi-arch Migration Status:** The `oc adm upgrade status` command now recognizes and reports on the progress of multi-arch migrations.  The output has been improved to clearly indicate when a migration is in progress and to provide more relevant information during this process.
* **Cluster Operator Status:** The update status now includes insights for each ClusterOperator resource, indicating whether the operator is updating, its target version, and its health status.  This information is available during control plane updates.
* **Version Pod Error Details:** The ClusterVersion status now includes more detailed error information when the version Pod encounters issues, such as signature validation failures or image pull errors. This replaces the previous less informative "Job was active longer than specified deadline" message.

**CVO Configuration and Logging:**

* **CVO Log Level API:** A new API has been introduced to configure the CVO's log level. This API is part of the `DevPreviewNoUpgrade` feature set and allows administrators to control the verbosity of CVO logs.  The CVO now reconciles this new CR and adjusts its logging level accordingly.  This functionality is also available in standalone OpenShift deployments.
* **Removal of USC Manifests from DevPreview:**  The Update Status Controller (USC) manifests have been removed from the DevPreview payload for 4.19, as no meaningful UpdateStatus API implementation is being shipped in this release.

**Upgrade Recommendations and Prechecks:**

* **Alert Integration with Upgrade Recommendations:** The tech-preview command `oc adm upgrade recommend` now includes relevant alerts as conditional update risks. This helps administrators identify potential issues before initiating an upgrade.  The command retrieves critical alerts, including `ClusterOperatorDown`, `PodDisruptionBudgetAtLimit`, `KubeNodeNotReady`, and `KubeNodeUnreachable`.
* **Upgrade Inhibition During Updates:** The CVO now prevents upgrades to a new minor version while an existing upgrade is in progress. This helps avoid issues that can arise from retargeting upgrades before a safe point is reached.  Z-stream upgrades are still allowed to ensure that critical fixes can be applied.


This summarizes the key user-facing changes in this OpenShift Over the Air update.  Further details can be found in the associated JIRA tickets and pull requests.

## OpenStack as Infra
## OpenStack as Infra Updates Summary

This release focuses on improving the management and distribution of CA certificates within the OpenStack environment, simplifying configuration for various services, and enhancing the Cinder CSI driver.

**CA Certificate Management Improvements:**

* The installer now adds the CA bundle to the root credential secret, streamlining the process of distributing certificates to services that require them.
* The Cloud Credential Operator (CCO) now consumes the CA certificate from the root credential secret and includes it in generated credential secrets. This simplifies configuration for services and eliminates the need for them to retrieve the CA bundle from multiple locations.
* Several components have been updated to consume the CA certificate from the CCO-provisioned credential secret, including:
    * CSI operator (for both Cinder and Manila CSI drivers)
    * Cloud Network Config Controller
    * Cluster Image Registry Operator
    * Machine API Provider for OpenStack (MAPO)
* Hypershift now uses the standard `cacert` key for the CA certificate, aligning with other components.

**Cinder CSI Driver Enhancements:**

* The `--with-topology` flag replaces the `--feature-gates=Topology` option for enabling topology awareness in the Cinder CSI driver. This simplifies configuration and aligns with the latest Kubernetes CSI best practices.

## Operator Runtime
## Operator Runtime Updates Summary

This release includes several new features and improvements to the Operator Lifecycle Manager (OLM):

**Operator Installation and Management:**

* **Single/OwnNamespace Install Mode (Tech Preview):**  Operators can now be installed in a single namespace or their own namespace, providing more granular control over operator deployments. This feature is controlled by the `NewOLMOwnSingleNamespace` feature gate.
* **Preflight Permissions Checks (Tech Preview):**  A preflight check has been added to verify operator permissions before installation, preventing potential installation failures due to insufficient permissions. This feature is controlled by the `NewOLMPreflightPermissionCheck` feature gate.

**Catalog Management:**

* **Catalog API Improvements (Tech Preview):** The catalog API has been enhanced with a new `/api/v1/metas` endpoint, providing improved performance and functionality for accessing catalog metadata. This feature is controlled by the `FeatureGateNewOLMCatalogdMetas` feature gate.

**Platform Updates:**

* **Controller Runtime and Kubernetes API Update:** The marketplace operator has been updated to controller-runtime v0.20.3 and Kubernetes API v0.32.3.
* **Kustomize Configuration Consolidation:** The `catalogd` and `operator-controller` Kustomize configurations have been consolidated for improved maintainability.
* **Feature Gate Management:** The cluster-olm-operator now watches and reconciles OpenShift feature gates, enabling dynamic control over OLM features based on feature gate settings.

## Origin Community Distribution of Kubernetes
## OKD Update Summary

This release introduces a significant change to the installation process:

* **Installer now uses CentOS Stream based bootimages:** OKD now utilizes pure CentOS Stream operating system boot images for installation, replacing the previous approach. This change simplifies the boot process and improves compatibility.

## OpenShift Dev Console
## OpenShift Dev Console Updates

This release focuses on merging the Admin and Developer perspectives for a more streamlined user experience, along with several usability improvements.

**Perspective Merge & Navigation:**

*   The Developer perspective is now disabled by default, with its functionality integrated into the Admin perspective. Admins can re-enable the Developer perspective via console settings.
*   All Developer perspective navigation items (Topology, Helm, Serverless functions, and Software catalog) are now available within the Admin perspective.
*   A guided tour introduces users to the unified Admin perspective and its features, including Quick Create.
*   The perspective switcher is hidden if only one perspective is enabled.
*   Perspective preference options are hidden in user preferences if only one perspective is available.

**Getting Started & Quick Starts:**

*   A "Getting Started" alert welcomes first-time users on the Software catalog, Helm repositories, and Helm releases pages.
*   The "Getting Started" section on the Cluster and Project overview pages now includes actions to start the Admin perspective guided tour and enable the Developer perspective.
*   A new quick start guides users on how to enable the Developer perspective.
*   All existing quick starts have been updated to reflect the merged perspective.

**Favorites:**

*   Users can now favorite pages in the Admin perspective, accessible from the left navigation.
*   The Favorites button now uses the page title as the default name, improving clarity.

**Topology:**

*   Numerous Topology components and utilities are now exposed to the `openshift-console/dynamic-plugin-sdk` for use in dynamic plugins.  These include: `CpuCellComponent`, `MemoryCellComponent`, `TopologyListViewNode`, `useOverviewMetrics`, `withEditReviewAccess`, `getPodMetricStats`, `getTopologyResourceObject`, `getResource`, `getTopologyEdgeItems`, `getTopologyGroupItems`, `getTopologyNodeItem`, `mergeGroup`, `getModifyApplicationAction`, `baseDataModelGetter`, `getWorkloadResources`, `contextMenuActions`, `CreateConnector`, and `createConnectorCallback`.

**Pipelines:**

*   The `CopyPipelineRunButton` component has been updated to use the PatternFly `ClipboardCopyButton` component, providing a more consistent user interface.  The dependency `react-copy-to-clipboard` has been removed.

**Serverless:**

*   Serverless CI tests now run in the Admin perspective.

**Other:**

*   The RHOAS plugin has been removed.

## OpenShift Console
## OpenShift Console Updates Summary

This release includes several updates and improvements to the OpenShift Console, focusing on dependency updates, PatternFly 6 adoption, and technical debt reduction.

**PatternFly 6 Adoption and UI/UX Improvements:**

* **PatternFly 6 Adoption:** The console has begun adopting PatternFly 6 components, resulting in a more modern and consistent user interface.  Several custom components have been replaced with their PatternFly 6 equivalents, including description lists, tabs, banners, checkboxes (replaced with switches), and the 404 page.  Work is ongoing to replace all instances of PatternFly 4.  The login page has also been updated.
* **Improved UI Consistency:**  Spacing of page elements has been aligned with PatternFly standards, and the LogViewer theme now dynamically responds to the user's selected console theme.  Bootstrap styles are being replaced with PatternFly equivalents.
* **New StorageClass Action:** Users can now set a default StorageClass directly within the UI.

**Dependency Updates and Tech Debt Reduction:**

* **Dependency Updates:** Several key dependencies have been updated, including Node.js (to v22), TypeScript (to v5), Webpack (to v5), i18next, and various React libraries.  This improves performance, security, and maintainability.  Efforts are underway to update the React dependency to a more recent version.
* **Technical Debt in Secret Components:** Several secret-related components have been refactored to improve code quality, type definitions, and maintainability.  This includes renaming components, migrating to functional components, and removing outdated patterns.
* **Polyfill Removal:**  Outdated polyfills for unsupported browsers have been removed, reducing the console's load time.
* **Legacy Component Removal:**  Several legacy custom components have been removed or replaced with PatternFly equivalents, simplifying the codebase and improving maintainability.
* **CLI Artifact Distribution:** The OpenShift CLI is now distributed for both RHEL8 and RHEL9.

**Other Enhancements:**

* **Identity Provider Deletion:** Administrators can now delete identity providers (IDPs) directly through the web console.
* **Job Creation Time Column:** A "Created Time" column has been added to the Job listing, allowing users to sort jobs by their creation date.


This summary highlights the most significant user-facing changes in this release.  Further details can be found in the associated JIRA tickets and GitHub pull requests.

## OpenShift Node
## OpenShift Node Updates Summary

**Image Security Enhancements:**

* **Bring Your Own Public Key Infrastructure (BYOPKI) for Image Verification (Tech Preview):**  Allows administrators to verify container images using their own Certificate Authority (CA) through updates to the `ClusterImagePolicy` and `ImagePolicy` Custom Resource Definitions (CRDs). This enables stronger control over image trust and provenance.  The container runtime config controller now rolls out BYOPKI configuration from these CRDs to the `policy.json` file.  New fields have been added to the `ClusterImagePolicy` API to support this functionality. (OCPNODE-2340, OCPNODE-2339, OCPNODE-3039, OCPNODE-2269)

**Node Configuration and Management:**

* **Removal of Cgroups v1 Support:** OpenShift now exclusively uses Cgroups v2.  Support for configuring Cgroups v1 has been removed from the `nodes.config.openshift.io` object.  Clusters using Cgroups v1 will be marked as not upgradeable to encourage migration to Cgroups v2. (OCPNODE-3020, OCPNODE-2877, OCPNODE-2842, OCPNODE-2841)
* **Minimum Kubelet Version Admission:** A new admission controller feature has been added to ensure all kubelets in the cluster meet a specified minimum version. This helps maintain cluster consistency and stability. (OCPNODE-2940)

**API Updates:**

* **ClusterImagePolicy and ImagePolicy API Promoted to v1:** The `ClusterImagePolicy` and `ImagePolicy` APIs have been promoted to v1, marking them as stable and ready for general use. This signifies the official support for Sigstore image verification in OpenShift. (OCPNODE-2619)

**User Namespaces:**

* **General Availability (GA) of User Namespaces:** User Namespaces are now generally available, enabling enhanced security and support for nested container use cases.  Security Context Constraints (SCC) support has been improved, and thorough testing has been conducted to ensure stability and reliability. (OCPNODE-2506)

## OpenShift Cloud
## OpenShift Cloud Update Summary

This release includes several enhancements related to Cluster API (CAPI) support, AWS functionality, and autoscaling.

**Machine API (MAPI) to CAPI Migration (Tech Preview):**

* **Migration Core Implemented:** The core tooling for migrating from MAPI to CAPI is now in place. This includes controllers and logic to handle the transition of authority between MAPI and CAPI, ensuring a smooth migration process for individual providers.  ([OCPCLOUD-2120](https://issues.redhat.com/browse/OCPCLOUD-2120))
* **Machine and MachineSet Conversion:** Bi-directional conversion between MAPI and CAPI Machines and MachineSets is now supported. This includes handling owner references, labels, annotations, and infrastructure specifics. ([OCPCLOUD-2644](https://issues.redhat.com/browse/OCPCLOUD-2644), [OCPCLOUD-2645](https://issues.redhat.com/browse/OCPCLOUD-2645), [OCPCLOUD-2647](https://issues.redhat.com/browse/OCPCLOUD-2647), [OCPCLOUD-2716](https://issues.redhat.com/browse/OCPCLOUD-2716), [OCPCLOUD-2880](https://issues.redhat.com/browse/OCPCLOUD-2880))
* **Deletion Synchronization:** Deletion mechanics are synchronized between MAPI and CAPI mirrored resources, ensuring consistent behavior for higher-level objects like the cluster autoscaler. ([OCPCLOUD-2648](https://issues.redhat.com/browse/OCPCLOUD-2648))
* **Migration Controller:** A dedicated controller manages the authority transitions between MAPI and CAPI, simplifying the migration logic and improving testability. ([OCPCLOUD-2564](https://issues.redhat.com/browse/OCPCLOUD-2564))

**AWS Enhancements:**

* **Elastic Fabric Adapter Support:** Elastic Fabric Adapter (EFA) is now supported for AWS deployments, enabling high-performance computing workloads. ([OCPCLOUD-2895](https://issues.redhat.com/browse/OCPCLOUD-2895))
* **Credentials Secret Conversion:**  Handles the conversion of AWS credentials secrets from MAPI to CAPI. ([OCPCLOUD-2713](https://issues.redhat.com/browse/OCPCLOUD-2713))
* **Security Group Handling:** Improved handling of security groups during MAPI/CAPI conversion ensures consistent security configurations. ([OCPCLOUD-2712](https://issues.redhat.com/browse/OCPCLOUD-2712))
* **EBS Volume Size Handling:** Addresses the handling of EBS volume sizes during conversion, providing a default size when not specified in MAPI. ([OCPCLOUD-2718](https://issues.redhat.com/browse/OCPCLOUD-2718))
* **AWS Capacity Blocks for ML:** MAPI now supports AWS Capacity Blocks, enabling better control over instance availability for machine learning workloads. ([OCPCLOUD-2780](https://issues.redhat.com/browse/OCPCLOUD-2780))

**Core CAPI Improvements:**

* **Machine to Node Label/Annotation Propagation:** Labels and annotations from CAPI Machines are now propagated to their corresponding nodes, maintaining consistency and enabling node selection based on machine properties. ([OCPCLOUD-2680](https://issues.redhat.com/browse/OCPCLOUD-2680), [OCPCLOUD-2860](https://issues.redhat.com/browse/OCPCLOUD-2860))
* **Cluster Object Generation:**  The CAPI operator now ensures a Cluster object exists for upgraded clusters in the `openshift-cluster-api` namespace. ([OCPCLOUD-2202](https://issues.redhat.com/browse/OCPCLOUD-2202))

**Autoscaling:**

* **Updated Autoscaling Annotations:** The cluster autoscaler now recognizes both upstream and OpenShift-specific scale-from-zero annotations, preferring the upstream version. This improves compatibility and simplifies debugging. ([OCPCLOUD-2500](https://issues.redhat.com/browse/OCPCLOUD-2500))

**Azure Service Operator:**

* **OpenShift Build:** The Azure Service Operator (ASO) is now built within OpenShift, streamlining the deployment process for the Cluster API Provider Azure (CAPZ). ([OCPCLOUD-2642](https://issues.redhat.com/browse/OCPCLOUD-2642))

**Rebasebot:**

* **Lifecycle Hooks:** Rebasebot now supports lifecycle hooks, enabling custom tooling to be run before, during, or after rebasing CAPI provider repositories. This improves automation and reduces maintenance overhead. ([OCPCLOUD-2593](https://issues.redhat.com/browse/OCPCLOUD-2593), [OCPCLOUD-2824](https://issues.redhat.com/browse/OCPCLOUD-2824))


**GCP Confidential VM Support:**

* **AMD SEV-SNP and Intel TDX:** Added support for deploying Confidential VMs on GCP using both AMD SEV-SNP and Intel TDX technologies, enhancing data-in-use protection. ([OCPCLOUD-2882](https://issues.redhat.com/browse/OCPCLOUD-2882), [OCPCLOUD-2889](https://issues.redhat.com/browse/OCPCLOUD-2889))

## OpenShift Application Platform Engineering
## OpenShift Application Platform Engineering Updates

This release includes enhancements to Control Plane Machine Set (CPMS) naming and Router certificate management.

**Control Plane Machine Naming Customization (GA)**

The `machineNamePrefix` field in the ControlPlaneMachineSet spec is now generally available.  This allows administrators to define a custom prefix for Control Plane Machine names, replacing the previous label and role-based naming convention.  The machine name will consist of the specified prefix, followed by a random string and the machine index.  This feature was previously in Tech Preview and is now enabled by default.  (OAPE-142, OAPE-16, OAPE-19, OAPE-18)

**Router External Certificate Support (GA)**

The `Route.spec.tls.externalCertificate` field is now generally available, allowing the use of certificates stored in secrets for Routes.  Remember that the Router service account requires read-only access to the referenced secret. Consult the OpenShift documentation for details on granting necessary permissions. (OAPE-26, OAPE-94, OAPE-92, OAPE-91)

**API Updates**

* The OpenShift API has been updated to reflect the changes for both CPMS MachineNamePrefix and Route ExternalCertificate features. (OAPE-96)

## Network Observability
## Network Observability Updates

This release focuses on improving the user experience for installing and managing Network Observability.

**Simplified Installation and Getting Started:**

* A new quickstart guide is available directly within the OpenShift Container Platform (OCP) console's help menu. This guide provides step-by-step instructions for installing and configuring Network Observability, along with an overview of resource usage and capabilities.
* A direct download link for the Network Observability command-line interface (CLI) has been added to the OCP console.

**Enhanced Configuration and Status Monitoring (NETOBSERV-1940):**

A new view within the Network Observability console plugin simplifies FlowCollector configuration and provides essential status information. This addresses limitations of the previous OpenShift Lifecycle Management (OLM) installation form and offers a more user-friendly experience.  Key features of this new view include:

* Streamlined FlowCollector configuration.
* Status information for the FlowCollector, including component readiness and warnings.
* Configuration recommendations and warnings, such as suggesting Kafka installation based on node count.
* LokiStack status and readiness information (when applicable).
* A FlowMetrics section displaying installed metrics, estimated and actual cardinality.
* Links to relevant Network Observability dashboards.

## Network Edge
# Network Edge Updates

## Gateway API

* **General Availability:** The Gateway API is now generally available. This includes full lifecycle management of Gateway API custom resource definitions (CRDs) by the cluster ingress operator.  The `GatewayAPI` and `GatewayAPIController` feature gates are now enabled by default. ([NE-2009](https://github.com/example/1221), [NE-2009](https://github.com/example/1216), [NE-2009](https://github.com/example/2261), [NE-2009](https://github.com/example/2281), [NE-2017](https://github.com/example/2284))
* **CRD Management:** The cluster ingress operator now manages the lifecycle of Gateway API CRDs.  A validating admission policy prevents modifications to these CRDs by any component other than the operator. This includes both standard and experimental Gateway API CRDs. ([NE-1953](https://github.com/example/1192), [NE-1953](https://github.com/example/1200), [NE-1969](https://github.com/example/1205), [NE-1969](https://github.com/example/1202))
* **OSSM 3.0 Upgrade:** The cluster ingress operator now installs OpenShift Service Mesh (OSSM) 3.0, which is required for Gateway API support.  The operator also manages the OSSM subscription to ensure compatibility. ([NE-1907](https://github.com/example/1112), [NE-1934](https://github.com/example/1152))
* **DNS Management:** Enhanced DNS management for Gateway API resources.  DNS records are created and managed based on the hostnames defined in Gateway listeners.  The system correctly handles unique and overlapping hostnames, as well as cases where no hostname is specified. ([NE-1957](https://github.com/example/1213))
* **Must-Gather:** Gateway API resources are now included in must-gather results, simplifying troubleshooting. ([NE-1277](https://github.com/example/933))
* **Tech Preview Graduation:** The Gateway API has graduated from Dev Preview to Tech Preview. ([NE-1871](https://github.com/example/2081))

## GRPC Route

* **Conformance Testing:** GRPC Route support has been added to the conformance test suite. ([NE-2008](https://github.com/example/1208))

## Ingress Operator

* **Dynamic Configuration Manager:** The dynamic configuration manager is now enabled with safeguards to prevent excessive resource consumption. ([NE-1790](https://github.com/example/1174))
* **Kubernetes 1.32 Update:** The cluster ingress operator has been updated to use Kubernetes 1.32 packages. ([NE-1936](https://github.com/example/1184))
* **OWNERS Files:**  OWNERS files have been updated for improved maintainability. ([NE-1870](https://github.com/example/29247))
* **Keepalived Documentation:** Added instructions for keepalived-ipfailover image testing. ([NE-1908](https://github.com/example/198))
* **Gateway API Conformance Tests:** A Makefile target has been added to run the upstream Gateway API conformance tests. ([NE-1260](https://github.com/example/1176))

## OpenShift Top Level Product Strategy
## OpenShift NetEdge Enhancements:  Maintainability and Debugability

This initiative focuses on improving the long-term maintainability and debugability of the OpenShift NetEdge.  Instead of solely addressing individual bugs, teams will design and implement solutions to improve overall system robustness and diagnostic capabilities.  This proactive approach aims to simplify future problem determination, bug resolution, and feature implementation.  A key example is improving point-to-point network connectivity, which would enhance stability and diagnostics for several components, including Kuryr, OVS, legacy SDN, NetEdge, kube-apiserver, openshift-apiserver, authentication, and the console.  This strategic shift emphasizes investing in preventative measures and architectural improvements to reduce future technical debt and improve the overall developer and user experience.

## OpenShift Monitoring
## OpenShift Monitoring Updates

This release includes several enhancements related to Prometheus integration, Alertmanager configuration, and metrics server certificates.

**Prometheus Integration (MON-4103, MON-4126, MON-4207):**

* **Prometheus Operator Upgrade:** The Prometheus Operator has been upgraded to v0.81.0, bringing in upstream improvements and bug fixes.
* **Fallback Scrape Protocol:** A fallback scrape protocol (`PrometheusText1.0.0`) has been added to the ScrapeClass for backward compatibility with Prometheus v2. This ensures continued functionality during the transition to newer Prometheus versions.

**Alertmanager Configuration (MON-4043):**

* **Proxy URL for External Alertmanagers:** You can now configure a proxy URL when adding external Alertmanager instances. This is particularly useful for disconnected clusters where proxying the connection between Prometheus and Alertmanager is necessary.

**Metrics Server Certificates (MON-3866):**

* **Separate Metrics Client Certificate:** A separate metrics client certificate has been created for the metrics server, enhancing security and improving client identification.  This removes the previous dependency on the Prometheus certificate for the metrics server.

## Machine Config Operator

This release brings several enhancements to cluster management and diagnostics. The `must-gather` tool now collects `MachineConfigNode` and `PinnedImageSet` resources for improved troubleshooting.  New runbooks are available to assist with "HighOverallControlPlaneMemory", "SystemMemoryExceedsReservation", "MCDPivotError", "MCDRebootError", and "ExtremelyHighIndividualControlPlaneMemory" alerts, accessible directly from the alerts themselves.  The Machine Config Operator (MCO) now uses the official Multi-Cluster Network (MCN) V1 and Pinned Image Sets (PIS) V1 APIs, and supports the Ignition 3.5 configuration format. New clusters on AWS and GCP automatically use the latest boot image, configurable via the `spec.managedBootImages` field in `MachineConfiguration` objects.  The MCO also uses the v1 MachineConfigNode (MCN) API, and automatically uses the global pull secret for pulling base images if no specific secret is defined in `MachineOSConfig`.  Container builds now incorporate files from `/etc/containers` for consistent runtime settings, enabling offline container image builds. Machine config nodes (MCNs) now fully support custom machine config pools (MCPs), displayed via `oc get machineconfignode`. The boot image controller automatically upgrades user-data Ignition stubs from version 2 to 3. The MCO allows cluster upgrades during scaling events. Management cluster and console certificate management has been improved.  The Managed OpenShift API and the On-Cluster Build feature now have generally available v1 APIs. Cluster administrators can trigger rebuilds of layered MachineConfigPools and MachineOSBuilds using annotations. The MCD provides earlier warnings for potential drain failures. The Machine Configuration's `ManagedBootImages` feature supports opting out of boot image updates. Automated MOSB image lifecycle management removes associated OCL images when the MOSB is deleted. The MCN API is now at V1, introducing MachineConfigNodes for granular control over node configurations. The Machine Controller manages user-data secrets for MachineSets and re-enables automatic MCS CA rotation. Machine config drift management automatically reconciles bootstrap and in-cluster configurations.  The MCD preserves logs from previous boots in `/etc/machine-config-daemon/previous-logs/`.


This release introduces Pinned Image Sets, allowing you to store container images locally for faster startup in network-constrained environments. The Pinned Image Set API is now generally available.  The Machine Config Node (MCN) feature and its API are also generally available, laying the groundwork for Pinned Image Sets.  On-Cluster Layering (OCL) is now generally available, with key enhancements including configuration reversion, automatic image build retries, disconnected environment support, and node resynchronization without reboots.  Boot image updates on GCP and AWS are now automatic (opt-out available). The system has been upgraded to Ignition spec 3.5, unlocking new RHCOS functionalities.  The Machine Config Operator (MCO) now automates MCS ignition CA certificate rotation and manages the user-data secret, with updated documentation available.  MCO error messaging has been significantly improved with more detailed and actionable information.  On-cluster builds now function in disconnected environments.  MCO has been updated to Kubernetes 1.32.  Finally, cluster storage management is improved with automatic removal of unused OS images when their corresponding MachineOSBuild object is deleted.


## OpenShift Image Registry
## OpenShift Image Registry Updates

**Support for New AWS Regions (IR-513, IR-522)**

The Image Registry now automatically supports new AWS regions without requiring code changes.  This eliminates manual updates and streamlines the onboarding process for OpenShift managed services like ROSA and OSD in new regions. Previously, new AWS regions required manual code updates to the Cluster Image Registry Operator (CIRO), blocking deployments and testing.

## OpenShift Hosted Control Plane
## OpenShift Hosted Control Plane Updates

This release introduces several enhancements related to Karpenter integration, control plane component management, and platform updates.

**Karpenter Integration Enhancements:**

* **Simplified Karpenter Management:** A new `OpenshiftEC2NodeClass` CRD is introduced as the primary interaction point for users, replacing direct interaction with `EC2NodeClass` objects. This simplifies Karpenter management and provides better control over future API changes. (HOSTEDCP-2262)
* **Vendored Karpenter CRDs:** Karpenter CRDs are now vendored in Hypershift, allowing users to create and update Karpenter resources directly without dealing with unstructured types. (HOSTEDCP-2257)
* **Automated Machine Approval:** Karpenter instances are now automatically approved, reducing operational burden.  This includes automated approval for both kubelet client CSRs and serving CSRs. (HOSTEDCP-2222, HOSTEDCP-2234, HOSTEDCP-2237)
* **Programmatic Userdata Generation:** Userdata for Karpenter is now generated programmatically, replacing the previous method of using a mock nodePool. (HOSTEDCP-2249)
* **Shared Ownership of Karpenter CRs:**  A ValidatingAdmissionPolicy for the Karpenter EC2NodeClass CRD prevents updates to managed fields, ensuring the service provider retains control over critical operational parameters like userdata and AMI.  Default values are provided for subnetSelectorTerms and securityGroupSelectorTerms if not set. (HOSTEDCP-2226)
* **Karpenter Prototype:** A feature-gated prototype integrates Karpenter with HCP, enabling Karpenter to manage the node lifecycle when the `--auto-node` flag is used during cluster creation. This prototype includes a self-contained Karpenter operator built into the HO image. (HOSTEDCP-2220)

**Control Plane Component Management:**

* **Improved Component Deletion:** Control plane components and their associated resources are now correctly deleted when their predicate changes to false, ensuring proper cleanup. (HOSTEDCP-2256)

**Platform Updates:**

* **IBM PowerVS Networking:**  The deprecated IBM Cloud Connection is replaced with IBM Transit Gateway as the default networking mode for PowerVS Hypershift clusters. (HOSTEDCP-2231)
* **HostedCluster API Validation and Docs:** Missing API validation and documentation for HostedCluster are added. (HOSTEDCP-2075)
* **Control Plane Pod Labeling:** A mechanism is added to label all pods in the control plane namespace, enabling compliance with secure supply chain requirements. (HOSTEDCP-2004, HOSTEDCP-2120)
* **Hypershift Operator Upgrade Testing:** A new test validates that Hypershift Operator upgrades do not cause unnecessary node rollouts. (HOSTEDCP-1971)

## OpenShift Etcd
OpenShift etcd has been updated with several rebases to newer upstream versions:

* **Etcd updated to 3.5.18:**  OpenShift etcd in 4.19 has been rebased to upstream etcd version 3.5.18.
* **Etcd updated to 3.5.19:** OpenShift etcd in 4.19 has been rebased to upstream etcd version 3.5.19.
* **Etcd updated to 3.5.21:** OpenShift etcd in 4.19 has been rebased to upstream etcd version 3.5.21.

A new configuration option has been added:

* **Configurable etcd container removal:** A new configuration option allows removal of the etcd container from the static pod manifest. This is intended to support transitioning etcd management to Pacemaker while preserving existing installation, upgrade paths, and operator functionality.  This feature is currently on hold for testing.

## OpenShift Installer
## OpenShift Installer Updates Summary

This summary highlights key user-facing changes, improvements, and new features in the OpenShift Installer.

**GCP Custom API Endpoints (Tech Preview)**

Several updates enable using custom GCP API endpoints, including private and restricted endpoints, for enhanced security and compliance:

* **Install Config:** Users can now specify custom endpoints in the install config, including validation to ensure correctness. ([CORS-3835](https://github.com/openshift/installer/pull/9363), [CORS-3917](https://github.com/openshift/installer/pull/9517))
* **API Integration:** The API now supports custom endpoints with appropriate tagging for tech preview and upgrade restrictions. ([CORS-3842](https://github.com/openshift/installer/pull/2150))
* **Installer Feature Gate:** A tech preview feature gate is added to the installer for custom endpoints. ([CORS-3843](https://github.com/openshift/installer/pull/9501))
* **Component Integration:**  Custom endpoints are now integrated into various cluster components:
    * Cluster Infrastructure Manifest ([CORS-3919](https://github.com/openshift/installer/pull/9518))
    * CAPG ([CORS-3918](https://github.com/openshift/installer/pull/9528))
    * Cloud-provider-gcp ([CORS-3908](https://github.com/openshift/installer/pull/9600))
    * MAPI for GCP ([CORS-3906](https://github.com/openshift/installer/pull/111))
    * GCP PD CSI Driver ([CORS-3911](https://github.com/openshift/installer/pull/141))
    * Cluster Ingress Operator ([CORS-3907](https://github.com/openshift/installer/pull/1197))

**AWS Networking Enhancements**

* **Subnet Selection:** Users can now specify subnets with roles (e.g., ClusterNode, IngressControllerLB) in the install config for finer control over network configuration. The `platform.aws.subnets` field is deprecated in favor of `platform.aws.vpc.subnets`. ([CORS-3867](https://github.com/openshift/installer/pull/9443), [CORS-3868](https://github.com/openshift/installer/pull/9655))
* **Subnet Validations:** Static and API-based validations are added for subnet configurations, including checks for duplicates, valid IDs, and role compatibility. ([CORS-3869](https://github.com/openshift/installer/pull/9505), [CORS-3870](https://github.com/openshift/installer/pull/9599), [CORS-3870](https://github.com/openshift/installer/pull/9663))
* **Component Placement:**  The installer now places API load balancers, ingress load balancers, and machines in specific subnets based on assigned roles. ([CORS-3871](https://github.com/openshift/installer/pull/9633), [CORS-3872](https://github.com/openshift/installer/pull/9633), [CORS-3873](https://github.com/openshift/installer/pull/9633))
* **Public IP Support:**  Creating IPI AWS clusters with public-only networking (NAT-less) and managed VPC is now supported. ([CORS-3936](https://github.com/openshift/installer/pull/9544))

**Azure Updates**

* **Managed Identity Control:**  Automatic creation of managed identities for Azure nodes is removed, giving users more control and reducing required permissions.  The API now allows configuring user-assigned or system-assigned identities for nodes. ([CORS-3883](https://github.com/openshift/installer/pull/9538), [CORS-3883](https://github.com/openshift/installer/pull/9625), [CORS-3883](https://github.com/openshift/installer/pull/133))
* **Azure Stack CAPI Integration:** Azure Stack infrastructure provisioning is now handled by CAPI. ([CORS-3959](https://github.com/openshift/installer/pull/9645), [CORS-3959](https://github.com/openshift/installer/pull/9666), [CORS-3864](https://github.com/openshift/installer/pull/9666), [CORS-3861](https://github.com/openshift/installer/pull/9538))
* **Boot Diagnostics:**  Support added for enabling boot diagnostics on worker nodes during installation for improved debugging. ([CORS-3854](https://github.com/openshift/installer/pull/9125))
* **NVMe Disk Support:** Added support for NVMe disk controllers on Azure. ([CORS-3825])
* **Dxv6 Machine Series Support:** Added support for the Dxv6 and Dsv6 machine series on Azure. ([CORS-3771])

**IBM Cloud Updates**

* **CAPI Provider Transition:** Terraform is replaced with the CAPI provider for IBM Cloud installations. ([CORS-3278](https://github.com/openshift/installer/pull/9652), [CORS-3278](https://github.com/openshift/installer/pull/9649), [CORS-3278](https://github.com/openshift/installer/pull/9636), [CORS-3278](https://github.com/openshift/installer/pull/9523))

**Other Improvements**

* **ARO Build Flag Removal:** The ARO build flag is removed from the installer. ([CORS-3855](https://github.com/openshift/installer/pull/9124))
* **Terraform Removal:** Terraform is removed from the installer. ([CORS-3960](https://github.com/openshift/installer/pull/9673))
* **OWNERS Files:** Added OWNERS files for platform providers. ([CORS-3637](https://github.com/openshift/installer/pull/9407))
* **Unused AWS Permission Removal:** The unused `autoscaling:DescribeAutoScalingGroups` IAM permission is removed. ([CORS-2508](https://github.com/openshift/installer/pull/9223))

**GCP Confidential VM Support (In Progress)**

* Work is in progress to add support for deploying Confidential VMs on GCP using AMD SEV-SNP ([CORS-3923](https://github.com/openshift/installer/pull/9395)) and Intel TDX ([CORS-3927](https://github.com/openshift/installer/pull/9395)).


This summary provides a high-level overview of the key changes.  Refer to the linked JIRA tickets and pull requests for more detailed information.

## OpenShift Core Networking
## OpenShift Core Networking Updates Summary

**Universal Connectivity & Localnet Enhancements (4.19 and 4.20)**

* Improved user experience for connecting Pods and VMs to physical networks using OVN Kubernetes localnet.
* ClusterUserDefinedNetworks (CUDN) now supports creating localnet topology networks.  Changes to the CUDN CRD have been replicated to CNO.
* User input validation for MTU, VLAN, and physnet name within CUDN configurations, with improved error messaging for invalid physical network names.
* Ability to reference a single "bridge-mappings" "localnet" from multiple UDNs.
* Default MTU for localnet set to 1500.
* Pods requesting a UDN without a VLAN can connect to services running on the host's network.
* Platform-managed scheduling for Pods requesting a localnet UDN, ensuring placement on nodes with available resources.

**OVN-Kubernetes BGP Support (4.18 and 4.20)**

* Enabled BGP support in OVN-Kubernetes when the corresponding OCP API flag is set.
* CNO now deploys the RouteAdvertisements OVN-K CRD.
* Route Advertisement API updated with a new universal network selector.
* Support added for Layer-2 UDNs in SGW.

**Whereabouts IPAM Performance and Scale Improvements**

* Fast ranges functionality integrated into CNO, improving IP allocation times.
* Opt-in functionality re-enabled for the node slice controller.

**Security Enhancements**

* Addressed security issues with CNO IPSec certificate signing by requiring the kubelet certificate in certificate requests.

**UDN API Improvements**

* Made IPAM options explicit in the UDN API to cater to common use cases and improve clarity.
* Support for `endPort` field added to MultiNetworkPolicy.
* Updated MultiNetworkPolicy CRD in CNO.

**OVS and Libreswan Updates**

* OVS updated to version 3.5.0-0.9, providing configuration flexibility for `openvswitch-ipsec`.
* Libreswan version unpinned in the ovnk image to consume the latest version from the FDP repo.
* Regex for the `ipsec showstates` command modified to support Libreswan 5.2.

**Cluster Network Operator (CNO) Improvements**

* CNO now reacts to Machine Config Pool status for improved IPsec rollout monitoring.
* CNO kube version rebased to 1.32.
* Improved handling of workload provisioning by ensuring network creation has started.

**Other Notable Changes**

* Downstream merge for fast range fixes and dependency bumps in Whereabouts.
* L2 NetworkPolicy support enabled on primary UDNs.


This summary highlights the key user-facing changes and improvements in OpenShift Core Networking.  For detailed information, please refer to the individual JIRA tickets and GitHub pull requests.

## OpenShift Virtualization
## OpenShift Virtualization Updates

This release includes several user interface improvements, enhanced networking features, and improved alert management.

**User Interface Enhancements:**

* **Modernized UI Components:** Several UI components across the console, including tables, dropdowns, and modals, have been updated to the latest PatternFly 6 standards for a more consistent and modern look and feel.  This specifically impacts the Virtual Machine console, Networking UI, and Template Catalog.
* **Networking UI Overhaul:** The Networking user interface has received a significant upgrade to PatternFly 6, providing a more streamlined and intuitive experience.

**Networking:**

* **User-Defined Networks (UDN) UI:**  A new UI allows management of primary user-defined networks, including:
    * Creating ClusterUserDefinedNetworks with namespace selectors.
    * Defining UserDefinedNetworks within projects.
    * Automatic querying for UserDefinedNetwork creation when creating Pods/VMs in new projects.
    * Clearer "user-defined primary network" labeling for VMs running in namespaces with UDN defined.
    * Requesting specific IPs for VMs connected to UDN.
    * Project selection using `matchExpressions` for ClusterUDN.
    * Project search by name.
    * ClusterUDN creation modal.

**Alert Management:**

* **Aggregated Alerts:** The Alerts page now aggregates alerts by name and severity, making it easier to identify and manage recurring issues.  The total number of alerts for each type is displayed, and clicking on an aggregated alert expands to show the individual alert instances.

**Hypershift:**

* **Improved VM Distribution:**  Documentation has been added outlining how to configure the descheduler to better distribute VMs across nodes in a Hypershift node pool, improving high availability. This leverages `SoftTopologyAndDuplicates` profile and `TopologySpreadConstraints`.

## Cluster Integration and Delivery
# Cluster Integration and Delivery Updates

## Image Management

* **Resource Tracking:** Resources created by `oc-mirror` are now annotated with `createdBy: oc-mirror v2` for easier identification and management.  You can use this annotation to filter resources, for example: `oc get idms -o jsonpath='{.items?(@.metadata.annotations.createdBy=="oc-mirror v2").metadata.name}'`.
* **Container Image Signatures:** Cosign signature tags are now mirrored alongside container images for disk-to-mirror, mirror-to-disk, and mirror-to-mirror workflows. This includes signatures for additional images, catalog images, operator images, release images, and release payload images.  A manifest list image will have a signature tag for itself and for each manifest it includes.  Default configurations for signature mirroring and verification have been added for common registries, including internal registries, quay.io, and registry.redhat.com.  Users can now also skip signature mirroring and verification entirely if needed.

## CLI Enhancements

* **Cache Location:** The `oc-mirror delete` command now supports a `--cache-dir` option to specify the location of the cache directory. This provides a more discoverable alternative to the `OC_MIRROR_CACHE` environment variable.

## Breaking Changes

* **Selected Bundles Feature Removed:** The selected bundles feature has been removed due to potential issues.

## OpenShift CFE
## OpenShift CFE Updates

This release introduces a new feature that allows customizing control plane machine names using a prefix.

**Customizable Control Plane Machine Names (CFE-1167 & CFE-1168):**  A new `MachineNamePrefix` field has been added to the `ControlPlaneMachineSet` object. This field allows you to specify a custom prefix for the names of your control plane machines. This feature is controlled by the `CPMSMachineNamePrefix` feature gate, which must be enabled to use this functionality.

## OpenShift Cloud Credential Operator
## OpenShift Cloud Credential Operator Updates

This release includes several enhancements and upgrades:

**Security & Stability:**

* **Read-Only File System for Pods:**  All Cloud Credential Operator pods now use a read-only root file system for improved security. This change involved reverting a previous modification to how TLS CA bundles are mounted.

**Dependency Upgrades:**

* **Kubernetes 1.32 Upgrade:** The operator has been upgraded to use Kubernetes 1.32, ensuring compatibility with the latest OpenShift clusters and incorporating upstream improvements.
* **Vendor Dependency Updates:**  Various Go dependencies have been updated to their latest versions to improve security and address potential vulnerabilities.

**Logging & Diagnostics:**

* **Improved Credentials Request Logging:** When the Cloud Credential Operator updates the status of a CredentialsRequest, the logs now include a diff showing the specific changes made. This enhancement improves troubleshooting, particularly for identifying issues like update loops.

## OpenShift Autoscaling
## OpenShift Autoscaling Updates Summary

**Hypershift AutoNode Enhancements:**

* **Karpenter Image Management:** The Hypershift AutoNode implementation now uses the `aws-karpenter-provider-aws` image included in the OpenShift release payload.  If the image is not present in the payload, it falls back to the upstream image. This allows for better integration and testing of OpenShift's specific Karpenter provider.  Additionally, an HCP annotation can be used to override the `aws-karpenter-provider-aws` image, enabling developers to test different versions.
* **AutoNode Upgrades:** Hosted cluster upgrades now trigger Karpenter drift, ensuring that the RHCOS and Kubernetes versions of the nodes match the versions in the new release payload. Workloads are automatically rescheduled to the new nodes after the upgrade. An end-to-end test has been added to verify this functionality.
* **AutoNode Deletion:** When an HCP cluster with AutoNode is deleted, Karpenter-provisioned nodes and their corresponding instances are now automatically removed to prevent resource leaks.

**Karpenter Provider for AWS:**

* **Release Automation:** A release job has been created to run end-to-end tests for the `karpenter-provider-aws` image.

## OpenShift Authentication
## OpenShift Authentication Updates

This release introduces structured authentication configuration for Kubernetes API Server (KAS) pods using OpenID Connect (OIDC) and updates the kube-rbac-proxy.

**Structured OIDC Authentication Configuration:**

OpenShift now supports configuring OIDC authentication for KAS pods using a structured configuration.  The Cluster Authentication Operator (CAO) generates this configuration based on the authentication custom resource (CR) and stores it in a ConfigMap within the `openshift-config-managed` namespace.  The KAS operator (KAS-o) then synchronizes this ConfigMap to the KAS pods, enabling OIDC authentication via the `--authentication-config` command-line flag.  Existing authentication mechanisms managed by the `AuthMetadata` and `WebhookTokenAuthenticator` config observers are automatically disabled when OIDC is enabled via this new method.

**Kube-rbac-proxy Update:**

The kube-rbac-proxy has been updated to v0.18.2. This update prevents tokens from being logged, even when high verbosity logging is enabled.

## Agent-based Installer for OpenShift
## Agent-based Installer Updates

This release includes several enhancements to the agent-based installer, focusing on improved user experience, ISO generation, and platform support:

**Installation Workflow & User Interface:**

* **Interactive Installation Enhancements:** The installer now features an interactive TUI (text-based user interface) that guides users through the installation process.  This includes selecting the rendezvous node (node0) and verifying connectivity to it (AGENT-464, AGENT-1114). The TUI also displays the Web UI URL once the assisted service is available, allowing users to seamlessly transition to the graphical interface (AGENT-467).  The overall workflow for loading the agent UI has also been refined (AGENT-1113).
* **Certificate Generation:**  A new command, `openshift-install agent create certificates`, has been added to generate TLS certificates needed for the agent UI, simplifying the installation process (AGENT-537).

**ISO Generation and Management:**

* **Internal Registry Support:** The appliance builder now supports using an internal registry for release payloads, improving installation speed and reliability in disconnected environments (AGENT-1151).
* **Nightly/CI Release Payload Support:** The builder script can now use nightly/CI release payloads for testing and debugging, streamlining the development process (AGENT-1137).
* **ISO Bootability:** The generated ISO is now bootable from USB drives, providing more flexibility for users (AGENT-1188).
* **Streamlined ISO Contents:** The `setup-agent-tui.sh` script and agent TUI artifacts are now included within the ISO ignition file for better organization and consistency (AGENT-1150, AGENT-1118, AGENT-1119).

**Platform Support:**

* **Nutanix Integration:** The agent-based installer now supports Nutanix platform, expanding the range of deployment options (AGENT-587).

**Documentation:**

* **Improved Documentation:** Internal documentation for the installer and ISO builder has been updated to reflect the latest changes and provide better guidance for developers (AGENT-1159, AGENT-1154).

## On Prem Networking
## On Prem Networking Updates

**Improved Control Plane Stability (OPNET-629 & OPNET-579)**

The health checks for network components have been significantly improved.  Instead of relying on potentially unreliable API calls, the system now uses HAProxy's own monitoring endpoint to determine its health and the health of its backend services. This change makes the control plane more robust, especially in larger deployments and during upgrades, preventing unnecessary failovers and service disruptions.  This improvement addresses potential issues with incorrect health reporting during API rollouts and in scenarios with unhealthy cluster backends.

## OpenShift BuildConfig
## OpenShift BuildConfig Updates

This release focuses on improving the contributor experience for `openshift/builder`.

**Simplified Build Process & Documentation:**

* The build process has been streamlined.  A new universal `Containerfile` based on UBI9 replaces older, Red Hat specific Dockerfiles, making it easier for external contributors to build the project.  Red Hat internal builds now use a separate, dedicated `Containerfile`.  This simplifies the build process and removes confusion around RHEL versions. Dependencies are now always vendored, aligning with OpenShift standard practices.
* The contributor documentation has been significantly revamped.  It now includes comprehensive instructions for setting up a development environment, building, testing, and deploying `openshift/builder`.  Clearer guidance is provided for both community contributors and Red Hat employees, including information on using `cluster-bot` for automated testing.  The updated documentation provides more context and links to relevant resources, making it easier for new contributors to get started.  Contributors can now submit pull requests with only unit tests passing, simplifying the contribution workflow.

## OpenShift API Server
## OpenShift API Server Updates

This release introduces a TLS artifacts registry to better manage and track certificates and CA bundles within the cluster.  This registry will automatically collect existing certificates and their metadata, ensuring compliance with defined requirements.  A new feature, "ShortCertRotation," has also been added.  Additionally, descriptions for certificates managed by the `cluster-kube-apiserver-operator` are now included, improving clarity and maintainability.
