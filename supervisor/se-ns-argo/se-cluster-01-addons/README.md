# se-cluster-01 add-ons

VKS add-ons for `se-cluster-01`. They are **declared on the Supervisor** (an
`AddonConfig` + `AddonInstall` in `se-ns-argo`) and **VKS installs them into
the cluster** — so they live under `supervisor/` and belong to the
`supervisor-wld` project.

Kept apart from `../se-cluster-01/` on purpose: that app holds the Cluster CR
and must never prune or delete. Add-ons are safe to add and remove — deleting
an `AddonInstall` uninstalls the add-on, and a re-sync puts it back.

| File | Add-on | Release |
|---|---|---|
| `cert-manager.yaml` | cert-manager + self-signed ClusterIssuer `se-selfsigned` | 1.20.2 |

## ArgoCD app

```sh
argocd app create se-cluster-01-addons \
  --project supervisor-wld \
  --repo https://github.com/edric45/se-gitops.git \
  --revision main \
  --path supervisor/se-ns-argo/se-cluster-01-addons \
  --dest-name supervisor-se-ns-argo \
  --dest-namespace se-ns-argo \
  --sync-option ServerSideApply=true
argocd app sync se-cluster-01-addons
```

## Adding another add-on

1. See what is offered: `kubectl --context 172.17.10.2 get addonreleases -A`
2. See its settings: `kubectl --context 172.17.10.2 -n vmware-system-vks-public get addonconfigdefinition <release> -o yaml`
3. Copy `cert-manager.yaml`, change the names, `addonRef`, `releaseFilter` and `values`.

## Do not touch

The platform-owned add-ons (antrea, helm-controller, prometheus, telegraf,
vault-injector, ...) show up in `se-ns-argo` as `AddonConfig`/`ClusterAddon`
objects but are driven by `AddonInstall`s in `vmware-system-vks-public`.
Never delete them — see the root README.
