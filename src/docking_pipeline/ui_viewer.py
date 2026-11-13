"""Offline Plotly molecular coordinates; no external JavaScript CDN."""
from pathlib import Path
import numpy as np
import plotly.graph_objects as go
from rdkit import Chem
import gemmi


def pose_figure(sdf: Path, pose_index: int, receptor: Path | None=None, reference: Path | None=None):
    mol=Chem.SDMolSupplier(str(sdf),removeHs=True)[pose_index]
    if mol is None: raise ValueError('Unable to parse docked pose')
    figure=go.Figure()
    xyz=mol.GetConformer().GetPositions()
    if receptor and receptor.exists():
        structure=gemmi.read_structure(str(receptor))
        for chain in structure[0]:
            points=[]
            for residue in chain:
                atoms=[a for a in residue if a.name=='CA']
                if atoms:
                    p=atoms[0].pos
                    points.append([p.x,p.y,p.z])
            if points:
                backbone=np.asarray(points)
                figure.add_trace(go.Scatter3d(x=backbone[:,0],y=backbone[:,1],z=backbone[:,2],mode='lines',
                    line={'color':'#81998f','width':3},opacity=.3,name=f'Chain {chain.name} backbone',hoverinfo='skip'))
    if reference and reference.exists():
        structure=gemmi.read_structure(str(reference))
        points=np.asarray([[a.pos.x,a.pos.y,a.pos.z] for c in structure[0] for r in c for a in r if a.element.name!='H'])
        if len(points): figure.add_trace(go.Scatter3d(x=points[:,0],y=points[:,1],z=points[:,2],mode='markers',
            marker={'size':4,'color':'#d8a349','opacity':.65},name='Crystal reference',hoverinfo='name'))
    bx,by,bz=[],[],[]
    for bond in mol.GetBonds():
        a,b=xyz[bond.GetBeginAtomIdx()],xyz[bond.GetEndAtomIdx()]
        bx.extend([a[0],b[0],None]); by.extend([a[1],b[1],None]); bz.extend([a[2],b[2],None])
    figure.add_trace(go.Scatter3d(x=bx,y=by,z=bz,mode='lines',line={'color':'#658778','width':5},showlegend=False,hoverinfo='skip'))
    colors={'C':'#246654','N':'#3779c6','O':'#d4504d','S':'#cf9b25','F':'#64a46e','Cl':'#64a46e'}
    figure.add_trace(go.Scatter3d(x=xyz[:,0],y=xyz[:,1],z=xyz[:,2],mode='markers',name='Docked ligand',
        marker={'size':5,'color':[colors.get(a.GetSymbol(),'#996db1') for a in mol.GetAtoms()]},
        text=[f'{a.GetSymbol()} · atom {a.GetIdx()+1}' for a in mol.GetAtoms()],hovertemplate='%{text}<extra></extra>'))
    center=xyz.mean(axis=0); span=max(float(np.ptp(xyz,axis=0).max())/2+7,10)
    axes={name:{'visible':False,'range':[float(center[i]-span),float(center[i]+span)]} for i,name in enumerate(['xaxis','yaxis','zaxis'])}
    figure.update_layout(height=530,margin={'l':0,'r':0,'t':0,'b':0},paper_bgcolor='#f7f8f4',
        scene={**axes,'aspectmode':'cube','bgcolor':'#f7f8f4'},legend={'orientation':'h','y':0,'x':0},
        font={'family':'Arial','color':'#203d32'},uirevision=str(sdf))
    return figure
