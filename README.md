# se-gitops

The GitOps rebuild of the SE lab: ArgoCD on the vSphere Supervisor driving
cluster lifecycle, addons and workloads from git.

Separate from [`se-vks-platform`](../se-vks-platform), which is the imperative
Makefile-era version and stays as the working reference for addon manifests,
package value schemas and the Istio/pure-istio customer material.

## Current state — 2026-09-26

| | |
|---|---|
| Supervisor | `172.17.10.2` (`wkld01.vks.lab`) |
| ArgoCD namespace | `se-ns-argo` — created in the vCenter UI |
| ArgoCD instance | `phase: Ready`, `3.4.4+vmware.1-vks.1` |
| ArgoCD UI | https://172.17.10.26 — user `admin` |
| Cluster namespace | `se-ns-argo` too — everything lives in one vSphere Namespace |
| Workload cluster | **none.** `se-cluster-01` deleted 2026-09-25 to be rebuilt from git; manifest in `supervisor/se-ns-argo/se-cluster-01/` |
| `se-namespace` | the old cluster namespace — empty, no longer used |

The admin password was changed from the initial one on 2026-09-26, so
`argocd-initial-admin-secret` no longer holds it.

Registered clusters: `supervisor-se-ns-argo` → `https://172.17.10.2:443`,
scoped to `se-ns-argo` (see `bootstrap/15-register-supervisor.sh`).

## The architecture

One ArgoCD on the Supervisor, two destinations:

```
        GitHub  (source of truth; GitLab later)
          |
          v
  ArgoCD in se-ns-argo  (Supervisor, vSphere Pods)
          |
          +--> supervisor-se-ns-argo --> se-ns-argo
          |                               Cluster CR, AddonConfig, AddonInstall
          |
          +--> se-cluster-01 (registered once it exists)
                                workload namespaces and apps
```

ArgoCD and the Cluster CR share `se-ns-argo`, so one namespace-scoped
registration covers both. Deleting and rebuilding `se-cluster-01` does not touch
the namespace, so ArgoCD survives it — which is the whole point of the exercise.

What sharing costs:

- ArgoCD's pods and the cluster's VMs draw from the **same** namespace resource
  pool. No quota is set today; if one is added, size it for both.
- `argocd-manager` holds `edit` in `se-ns-argo`, which **includes deleting the
  Cluster**. The only guard is the `Prune=false,Delete=false` sync-option
  annotation on the Cluster CR — keep it.
- Never tear down `se-ns-argo` to reset the cluster. Delete the Cluster CR.

## Where git ownership starts, and why not earlier

Namespace Self-Service is not enabled on this Supervisor. The vSphere Namespace
itself, its storage-policy binding, VM-class binding, RBAC and resource-pool
limits are **vCenter-only** and ArgoCD can never own them. So git ownership
starts at the Cluster CR.

`kubectl auth can-i` and `--dry-run=server` both *lie* about this — they report
success and the real apply fails with
`User is not authorized to create selfservice namespaces`.

## Layout

```
bootstrap/     applied BY HAND. Everything that must exist before ArgoCD can
               take over. See bootstrap/README.md for the order.
supervisor/    Cluster CR, AddonConfig/AddonInstall      -> Supervisor, se-ns-argo
               + jumpbox/: browser-accessible debug desktop VM
```

Still to come:

```
gitops/        AppProjects + the app-of-apps leaf        -> Supervisor, se-ns-argo
clusters/      per-cluster platform + workload manifests -> the workload cluster
```

The top-level directory names the **API server**. That is the one thing to get
right: `supervisor/` and `clusters/<name>/` go to different endpoints, and a
manifest in the wrong tree either fails or does something surprising.

## Open items

- **Health checks not wired.** ArgoCD assesses unknown CRDs as Healthy
  immediately, so sync waves would fire the addon step while the cluster is
  still cloning VMs. `bootstrap/20-healthchecks.yaml.todo` has the Lua; it needs
  a live Cluster to confirm whether the condition is `Ready` or `Available`.
- **`ignoreDifferences` for the Cluster CR not derived.** The live Cluster YAML
  was not captured before the teardown (only table output, in
  `se-vks-platform/docs/teardown-inventory-2026-09-25.md`). It will have to come
  from observed drift after ArgoCD recreates the cluster.
- **Velero + MinIO.** MinIO is already installed as a Supervisor Service
  (`svc-minio-cly5e`, v2.0.10) and a `minio-vsan-sna-thick` StorageClass exists,
  so the backup target may not need building. No `Tenant` exists yet.
- **GitLab** deferred — no operator on this Supervisor, and it needs more
  capacity than the old 2×4-vCPU worker pool had.

## Things this lab has already taught us

**Pin `spec.version`, and expect it to need commits.** The supported-versions
list is mutable and revalidated every reconcile. `argocd-ks115` in `ks115-user`
pinned `3.0.19` (valid on 2026-08-31); the list moved on 2026-09-19 and it now
reports `PHASE: Failed` while all five pods run and its PackageInstall still
reconciles fine. Broadcom's docs still name `3.0.19` and `2.14.15` — both gone.

**There is no Supervisor Service to enable for ArgoCD.** The operator
(`argocd-service` 1.2.0, `svc-argocd-service-ix0im`) is built into the
Supervisor. `get supervisorservices` lists only MinIO. Applying the CR is the
whole install.

**Don't `delete addonconfig --all` in a cluster namespace.** `se-namespace` held
11 AddonConfigs but only 3 AddonInstalls; the other 8 are driven by
platform-owned AddonInstalls outside the namespace (`cni-addon-antrea-*`,
`vcfops-prometheus-addoninstall`, `vault-injector-global-installer`,
`builtin-helm-controller-addoninstall`, `vks-static-*-install`, `carvel-repo`,
`depot`). A blanket delete takes out the CNI.

**Two other ArgoCD namespaces exist and neither is ours** — `ks115-user` (the
version-stranded one) and `argocd-instance-1` (74 days old, no ArgoCD object in
it at all). Leave both alone.
