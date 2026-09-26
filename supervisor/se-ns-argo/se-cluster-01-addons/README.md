# se-cluster-01 add-ons

VKS add-ons for `se-cluster-01`. They are **declared on the Supervisor** (an
`AddonConfig` + `AddonInstall` in `se-ns-argo`) and **VKS installs them into
the cluster** — so they live under `supervisor/` and belong to the
`supervisor-wld` project.

**One folder per add-on.** The ApplicationSet in
[`gitops/applicationsets/se-cluster-01-addons.yaml`](../../../gitops/applicationsets/se-cluster-01-addons.yaml)
turns each folder into its own ArgoCD Application, `se-cluster-01-<folder>`,
which syncs automatically.

| Folder | Add-on | Release |
|---|---|---|
| `cert-manager/` | cert-manager + self-signed ClusterIssuer `se-selfsigned` | 1.20.2 |

Kept apart from `../se-cluster-01/` on purpose: that app holds the Cluster CR
and must never prune or delete. Add-ons are safe to add and remove.

## Adding an add-on

1. See what is offered: `kubectl --context 172.17.10.2 -n vmware-system-vks-public get addonreleases | grep <addon>`
2. See its settings (release name with `---` before `vmware`):
   `kubectl --context 172.17.10.2 -n vmware-system-vks-public get addonconfigdefinition <release> -o yaml`
3. Copy `cert-manager/` to `<addon>/`, rename the file, and change the object
   names, `addonConfigNameTemplate`, `addonRef`, `releaseFilter` and `values`.
4. Validate: `kubectl --context se-ns-argo apply --dry-run=server -f <addon>/`
5. Commit and push. The app `se-cluster-01-<addon>` appears and syncs.
6. Check: `kubectl --context se-ns-argo get clusteraddon se-cluster-01-<addon>` → READY True

## Removing an add-on

Delete its folder and push. The ApplicationSet deletes the app, the app's
finalizer deletes the `AddonInstall`/`AddonConfig`, and VKS uninstalls the
add-on from the cluster.

## Do not touch

The platform-owned add-ons (antrea, helm-controller, prometheus, telegraf,
vault-injector, ...) show up in `se-ns-argo` as `AddonConfig`/`ClusterAddon`
objects but are driven by `AddonInstall`s in `vmware-system-vks-public`.
Never delete them — see the root README.
