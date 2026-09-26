# bootstrap — the part that cannot be GitOps

Everything in this directory is applied **by hand**, because it is what has to
exist before ArgoCD can take over. Once `20-root-app.yaml` lands (not written
yet), the rest of the platform is driven by `git push`.

The hand-off line: **the vSphere Namespace, the ArgoCD instance, and the root
Application are manual. The Cluster CR and everything downstream of it is git.**

## Why the namespace is manual

Namespace Self-Service is not enabled on this Supervisor. The vSphere Namespace
itself, its storage-policy binding, VM-class binding, RBAC and resource-pool
limits are all vCenter-only. ArgoCD can never own them — so git ownership starts
at the Cluster CR, not the namespace.

Note that `kubectl auth can-i` and `--dry-run=server` both *lie* about this:
they report success and the real apply then fails with
`User is not authorized to create selfservice namespaces`.

## Order

### 0. Prerequisites — vCenter UI

Create the vSphere Namespace for ArgoCD. Here: **`se-ns-argo`**.

It needs a **storage policy** bound (ArgoCD runs as vSphere Pods, and cluster
nodes need it for their disks) and **VM classes** bound, because the workload
clusters live here too. Currently bound: `vsan-default-storage-policy` and
`best-effort-{xsmall,small,medium,large,xlarge}`.

ArgoCD and the clusters share this namespace so one namespace-scoped
registration covers both. Deleting a Cluster CR does not touch the namespace, so
ArgoCD outlives `se-cluster-01` being destroyed and rebuilt.

Verify:

```sh
kubectl --context 172.17.10.2 -n se-ns-argo get storageclass   # non-empty
kubectl --context 172.17.10.2 -n se-ns-argo get resourcequota  # note any caps
```

A resource quota here matters more than it looks: ArgoCD's pods draw from the
same vSphere Namespace resource pool as anything else in it. As of 2026-09-26
`se-ns-argo` has **no quota**, so there is no cap to collide with.

### 1. The ArgoCD instance

```sh
kubectl --context 172.17.10.2 apply -f bootstrap/10-argocd.yaml
kubectl --context 172.17.10.2 -n se-ns-argo get argocd,pods -w
```

There is **no Supervisor Service to enable first.** The operator
(`argocd-service` 1.2.0, in `svc-argocd-service-ix0im`) is built into the
Supervisor — it does not appear in `get supervisorservices`, and the only thing
that does is MinIO 2.0.10. Applying the CR is the entire install.

Expect five pods: `argocd-application-controller-0`, `argocd-redis-*`,
`argocd-redis-secret-init-*` (Completed), `argocd-repo-server-*`,
`argocd-server-*`.

Then the VIP and the admin password:

```sh
kubectl --context 172.17.10.2 -n se-ns-argo get svc argocd-server
kubectl --context 172.17.10.2 -n se-ns-argo get secret | grep -i admin
```

### 2. Register the Supervisor with ArgoCD

```sh
./bootstrap/15-register-supervisor.sh
```

Registers `https://172.17.10.2:443` as `supervisor-se-ns-argo`, scoped to
`se-ns-argo` only. Creates the `argocd-manager` SA, its token Secret and an
`edit` RoleBinding in `se-ns-argo`. Then adds
`https://github.com/edric45/se-gitops.git` as a repository (public, no
credentials).

## Version pinning is not optional here

`spec.version` is validated against a **mutable** list on every reconcile:

```sh
kubectl --context 172.17.10.2 get argocdversions argocd-supported-versions -o yaml
```

As of 2026-09-26 — `3.4.4` and `3.3.12` Recommended; `3.2.12` and `3.1.16`
upgrade-support-only. Broadcom's docs still name `3.0.19` and `2.14.15`; both are
gone from the list.

This lab already has the scar. `argocd-ks115` in `ks115-user` pinned `3.0.19`,
valid when created on 2026-08-31. The list moved on 2026-09-19 and the instance
is now `PHASE: Failed` — while all five pods are Running and its PackageInstall
still reconciles fine. **A healthy ArgoCD reporting Failed on version policy
alone.** Check the list before every upgrade and expect this field to need a
commit when it moves.

There is also an abandoned `argocd-instance-1` namespace (74 days old) with no
ArgoCD object in it at all. Neither of these is ours — don't touch either.

## Files

| File | |
|---|---|
| `10-argocd.yaml` | the ArgoCD instance in `se-ns-argo`, pinned to 3.4.4 |
| `15-register-supervisor.sh` | kube context, `argocd login`, `argocd cluster add` for the Supervisor, `argocd repo add` for this repo |
| `20-healthchecks.yaml.todo` | custom Lua health checks for `Cluster` / `ClusterAddon`. **Not ready** — needs a live Cluster to verify the condition types. Merge into `10-argocd.yaml` when it is. |
| `20-root-app.yaml` | not written yet — the one `kubectl apply` that hands over to git |

## Known gap

The live `Cluster` YAML was not captured before `se-cluster-01` was deleted on
2026-09-25 — only the table output, which is in the other repo at
`se-vks-platform/docs/teardown-inventory-2026-09-25.md`.
That YAML is what the `ignoreDifferences` list for the Cluster CR should have
been derived from. It will instead have to be derived by observing drift after
ArgoCD recreates the cluster:

```sh
kubectl -n se-ns-argo get cluster se-cluster-01 \
  -o jsonpath='{range .metadata.managedFields[*]}{.manager}{"\n"}{end}'
argocd app diff cluster-se-cluster-01
```

More iterative, not blocked.
