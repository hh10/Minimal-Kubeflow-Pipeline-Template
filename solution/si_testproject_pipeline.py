import os
import sys
import kfp
from kfp import dsl
from kubernetes.client.models import V1Volume, V1VolumeMount

_IMAGE = "eu.gcr.io/grand-kingdom-352313/test_proj_image2"
_PERSISTENT_VOL_CLAIM_PATH = "/mnt/pvolume"


def create_volume(size: str, vol_res_name: str = '', datasource_res_name: str = '', last_op=None):
    assert not vol_res_name or not datasource_res_name, print("Provide either 'vol_res_name' for new volume creation or 'datasource_res_name' for cloning it, not both")

    vname, data_source, access_mode = f"shared-volume-{size}", None, dsl.VOLUME_MODE_RWO
    if datasource_res_name:
        # a PVC claim to clone is provided
        data_source = "{{workflow.name}}-" + datasource_res_name
        vol_res_name = datasource_res_name + "-clone"
        vname += "-clone"
        access_mode = dsl.VOLUME_MODE_ROM

    vop = dsl.VolumeOp(
        name=vname,
        resource_name=vol_res_name,
        storage_class="standard-rwo",
        data_source=data_source,
        modes=access_mode,
        size=size,
    )
    return vop.after(last_op) if last_op else vop, vol_res_name


def release_pvc(pvc_res_name: str, last_op):
    pvc_release_cmd = 'kubectl delete pvc {{workflow.name}}-%s -n kubeflow --wait=false && \
                       kubectl patch pvc {{workflow.name}}-%s -n kubeflow -p \'{"metadata":{"finalizers": []}}\' --type=merge' % (pvc_res_name, pvc_res_name)
    return dsl.ContainerOp(
        name="release-shared-volume",
        image="google/cloud-sdk:216.0.0",
        command=["bash", "-c"],
        arguments=[pvc_release_cmd]).after(last_op)


def clone_repo(vop: dsl.VolumeOp, git_repo: str):
    repo_name = "cloned_repo"
    repo_path = os.path.join(_PERSISTENT_VOL_CLAIM_PATH, repo_name)
    cases_outpath = "/tmp/test.config"
    get_cases_args = f"rm -r {repo_path}; \
                       cat /root/.ssh/id_rsa; \
                       echo git clone {git_repo} {repo_path}; \
                       git clone {git_repo} {repo_path}; \
                       ls {repo_path}; \
                       python3 -c \"import os; import json; json.dump([os.path.join('{repo_path}', f) for f in os.listdir('{repo_path}') if os.path.isfile(os.path.join('{repo_path}', f))], open('{cases_outpath}', 'w'))\"; \
                       cat {cases_outpath};"
    return dsl.ContainerOp(
        name="get-files-from-repo",
        image=_IMAGE,
        command=["bash", "-c"],
        arguments=[f"{get_cases_args}"],
        file_outputs={"config": "/tmp/test.config"},
        pvolumes={_PERSISTENT_VOL_CLAIM_PATH: vop.volume},
    )


def node_op(filepath: str, gcs_results_location: str, vop_clone: dsl.VolumeOp, vol_clone_res_name: str):
    srun = dsl.ContainerOp(
        name="single-file-upload",
        image=_IMAGE,
        command=["bash", "-c"],
        arguments=[f'ls /mnt/pvolume/cloned_repo && sleep 15 && gsutil cp "{filepath}" "{gcs_results_location}"'],
    )
    # set these resource requests/limits to ensure that each pod is assigned to a single node/machine 
    srun.set_cpu_request("500m")
    srun.set_cpu_limit("800m")
    srun.add_volume(
        V1Volume(
            name=vop_clone.name,
            persistent_volume_claim={"claimName": "{{workflow.name}}-" + vol_clone_res_name, "readOnly": True},
        )
    )
    srun.add_volume_mount(V1VolumeMount(mount_path=_PERSISTENT_VOL_CLAIM_PATH, name=vop_clone.name, read_only=True))
    return srun


@dsl.pipeline(name="Verification pipeline", description="A simple pipeline that fetches a repo and uploads its files to a GCP bucket in parallel.")
def si_verpipeline(
    git_repo: str = "git@github.com:hh10/AIHack2022.git",
    gcs_results_location: str = "gs://si-testbucket-1",
    run_label: str = "default",
):
    vol_size = "1Gi"
    vop, vol_res_name = create_volume(vol_size, vol_res_name="pvc")
    repo_files = clone_repo(vop, git_repo)
    
    gcs_results_location = f"{gcs_results_location}/{run_label}/"
    vop_clone, vol_clone_res_name = create_volume(vol_size, datasource_res_name=vol_res_name, last_op=repo_files)
    with dsl.ParallelFor(repo_files.output).after(vop_clone) as filepath:
        single_result = node_op(filepath, gcs_results_location, vop_clone, vol_clone_res_name)
    # cleanup pv(c)s
    vop_clone_release = release_pvc(vol_clone_res_name, single_result)
    release_pvc(vol_res_name, vop_clone_release)


if __name__ == "__main__":
    assert len(sys.argv) == 2, print("only one input, i.e., output yaml path should be provided.")
    output_path = sys.argv[1]
    kfp.compiler.Compiler().compile(si_verpipeline, output_path)
    os.system(
        "sed -E -i \"s/^( *)add: \\['- SYS_ADMIN'\\]/\\1add:\\n\\1- SYS_ADMIN/g\" {pipeline}".format(
            pipeline=output_path
        )
    )
