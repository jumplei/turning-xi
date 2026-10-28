'use strict';
function overlayPayload(insight,metadata){
  if(!insight?.artifact_id||!insight.revision)return null;
  return {...insight,artifact_id:'overlay_'+insight.artifact_id,match_id:metadata.id,dataset_version:metadata.dataset_version,schema_version:'4.0'};
}
function correctionCounts(audit){
  const counts={insight:0,recap:0,overlay:0,phase:0};
  for(const operation of audit.operations||[])if(operation.operation==='withdraw'&&operation.kind in counts)counts[operation.kind]++;
  return {...counts,retained:(audit.retained_artifacts||[]).length};
}
if(typeof module!=='undefined')module.exports={overlayPayload,correctionCounts};
