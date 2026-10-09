"""Ejercicio 8: preservación, instantánea de tres años y evolución comparable."""
import argparse
import hashlib
import json
import os
from pathlib import Path

import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from benchmark import source_sql
from build_indicators import render_sql
from explore_parquet import ROOT, table

OUT=ROOT/'docs'/'resultados_ejercicio_8'
SNAPSHOT=ROOT/'data'/'processed'/'snapshot_antes_2025.json'


def snapshot():
    if SNAPSHOT.exists():
        print('Se conserva el snapshot anterior a 2025.');return
    rows=[]
    for p in sorted((ROOT/'data'/'raw').glob('*/*/*.parquet')):
        if p.parent.name not in ('2024','2026'):continue
        with p.open('rb') as f:sha=hashlib.file_digest(f,'sha256').hexdigest()
        st=p.stat();rows.append({'ruta':str(p.relative_to(ROOT)),'bytes':st.st_size,'mtime_ns':st.st_mtime_ns,'sha256':sha})
    if not rows:raise ValueError('Primero descargue 2024 y 2026')
    SNAPSHOT.parent.mkdir(parents=True,exist_ok=True)
    SNAPSHOT.write_text(json.dumps({'archivos':rows},indent=2)+'\n')


def complete():
    os.chdir(ROOT);OUT.mkdir(parents=True,exist_ok=True)
    validation=json.loads((ROOT/'docs'/'validacion_descarga_2024_2025_2026.json').read_text())
    if not validation['completo_segun_publicacion'] or set(validation['anios'])!={2024,2025,2026}:
        raise ValueError('Primero valide la descarga de los tres años')
    if not {2024,2025}.issubset(validation['anios_completos_requeridos']):raise ValueError('Exija 2024 y 2025 completos')
    baseline=json.loads(SNAPSHOT.read_text());preserved=[]
    for before in baseline['archivos']:
        p=ROOT/before['ruta'];st=p.stat()
        with p.open('rb') as f:sha=hashlib.file_digest(f,'sha256').hexdigest()
        ok=sha==before['sha256'] and st.st_size==before['bytes'] and st.st_mtime_ns==before['mtime_ns']
        if not ok:raise AssertionError('Cambió un archivo anterior: '+str(p))
        preserved.append({'ruta':before['ruta'],'sin_cambios':True,'sha256':sha})
    (OUT/'preservacion.json').write_text(json.dumps(preserved,indent=2)+'\n')
    paths=[r['ruta'] for r in validation['archivos']]
    level={'archivos':paths}
    sql=source_sql(level)
    fingerprint=[(p,(ROOT/p).stat().st_size,(ROOT/p).stat().st_mtime_ns) for p in paths]
    digest=hashlib.sha256((json.dumps(fingerprint)+sql).encode()).hexdigest()[:12]
    directory=ROOT/'data'/'processed'/'analitica';directory.mkdir(parents=True,exist_ok=True)
    target=directory/f'taxis_2024_2025_2026_{digest}.duckdb'
    if not target.exists():
        temporary=directory/f'construccion_{os.getpid()}.duckdb'
        print('Materializando instantánea de tres años:',validation['total_registros_metadata'],flush=True)
        with duckdb.connect(str(temporary)) as c:
            c.execute('SET threads=4');c.execute("SET memory_limit='2GB'")
            scratch=directory/f'tmp_{os.getpid()}';scratch.mkdir(exist_ok=True)
            c.execute("SET temp_directory='"+str(scratch)+"'")
            c.execute(sql)
            c.execute('CREATE TABLE viajes_duckdb AS SELECT * FROM viajes_parquet')
            c.execute('CHECKPOINT')
            assert c.execute('SELECT count(*) FROM viajes_duckdb').fetchone()[0]==validation['total_registros_metadata']
        temporary.replace(target)
    with duckdb.connect(str(target),read_only=True) as c:
        c.execute('SET threads=4');c.execute("SET memory_limit='1GB'")
        scratch=directory/f'lectura_{os.getpid()}';scratch.mkdir(exist_ok=True)
        c.execute("SET temp_directory='"+str(scratch)+"'")
        c.execute('CREATE TEMP VIEW viajes AS SELECT * FROM viajes_duckdb')
        c.execute((ROOT/'sql'/'eda'/'00_poblaciones.sql').read_text().replace('CREATE OR REPLACE VIEW','CREATE OR REPLACE TEMP VIEW'))
        frames={}
        for p in sorted((ROOT/'sql'/'evolucion').glob('*.sql')):
            print('Evolución:',p.stem,flush=True)
            frames[p.stem]=c.execute(p.read_text()).fetchdf();frames[p.stem].to_csv(OUT/(p.stem+'.csv'),index=False)
        assert int(frames['01_cobertura'].registros.sum())==validation['total_registros_metadata']
        checks=[]
        for folder in ('exploracion','eda','benchmark'):
            for p in sorted((ROOT/'sql'/folder).glob('*.sql')):
                if p.name.startswith('00_'):continue
                query=p.read_text().replace('{{fuente}}','viajes_duckdb')
                result=c.execute(query).fetchdf()
                checks.append({'consulta':str(p.relative_to(ROOT)),'estado':'OK','filas':len(result)})
        indicators=json.loads((ROOT/'docs'/'tablero'/'indicadores.json').read_text())
        for year in (2024,2025,2026):
            destination=OUT/f'indicadores_{year}';destination.mkdir(exist_ok=True)
            for item in indicators['indicators']:
                f=c.execute(render_sql((ROOT/item['sql']).read_text(),year,'all')).fetchdf()
                f.to_csv(destination/(item['key']+'.csv'),index=False)
                checks.append({'consulta':item['sql'],'anio':year,'estado':'OK','filas':len(f)})
        pd.DataFrame(checks).to_csv(OUT/'compatibilidad.csv',index=False)
    # Cambia de instantánea sin sobrescribir las bases y los tiempos del ejercicio 6.
    config_path=ROOT/'docs'/'tablero'/'indicadores.json'
    config=json.loads(config_path.read_text());config['database_file']=str(target.relative_to(ROOT))
    config['years']=[2024,2025,2026]
    config['evidence_dir']='docs/resultados_ejercicio_8/metabase'
    config_path.write_text(json.dumps(config,indent=2,ensure_ascii=False)+'\n')
    (OUT/'instantanea.json').write_text(json.dumps({'database_file':config['database_file'],'registros':validation['total_registros_metadata'],
        'archivos':len(paths),'bytes_duckdb':target.stat().st_size,'anteriores_preservados':len(preserved)},indent=2)+'\n')
    figures=ROOT/'docs'/'figuras_ejercicio_8';figures.mkdir(exist_ok=True)
    colors={2024:'#3877b5',2025:'#12806c',2026:'#bc8200'}
    monthly=frames['02_evolucion_mensual'];common=frames['03_periodo_comun']
    fig,axes=plt.subplots(1,2,figsize=(12,4))
    for ax,tipo in zip(axes,('yellow','green')):
        for year in (2024,2025,2026):
            d=monthly.loc[(monthly.anio==year)&(monthly.tipo_taxi==tipo)]
            ax.plot(d.mes,d.viajes_por_dia,label=str(year),color=colors[year],marker='.')
        ax.set(title=tipo,xlabel='Mes',ylabel='Viajes por día calendario');ax.set_xticks(range(1,13));ax.legend();ax.grid(alpha=.2)
    fig.suptitle('Evolución mensual — 2026 termina en el último mes publicado; escalas independientes')
    fig.tight_layout();fig.savefig(figures/'demanda_tres_anios.png',dpi=150,bbox_inches='tight');plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(15,4))
    for ax,metric,title in zip(axes,['viajes_por_dia','porcentaje_efectivo','total_mediano_usd'],['Demanda · 2024 = 100','Efectivo (%)','Total mediano aproximado (USD)']):
        for tipo,color in [('yellow','#bc8200'),('green','#12806c')]:
            d=common.loc[common.tipo_taxi==tipo]
            values=d[metric]
            if metric=='viajes_por_dia':values=100.0*values/d.loc[d.anio==2024,metric].iloc[0]
            ax.plot(d.anio,values,marker='o',label=tipo,color=color)
        ax.set(title=title,xlabel='Año');ax.set_xticks([2024,2025,2026]);ax.grid(alpha=.2);ax.legend()
    fig.suptitle('Comparación de meses comunes — importes nominales, poblaciones declaradas')
    fig.tight_layout();fig.savefig(figures/'comparacion_periodo_comun.png',dpi=150,bbox_inches='tight');plt.close(fig)
    findings=[]
    for tipo in ('yellow','green'):
        d=common.loc[common.tipo_taxi==tipo].set_index('anio');first,last=d.loc[2024],d.loc[2026]
        sequence=', '.join(f'{year}: {d.loc[year].viajes_por_dia:,.2f}' for year in (2024,2025,2026))
        findings.append(f'**Demanda {tipo}:** viajes diarios del período común: {sequence}. El cambio 2024→2026 es {100*(last.viajes_por_dia/first.viajes_por_dia-1):+.2f}%. Se ajustan días calendario, incluido febrero bisiesto de 2024.')
        findings.append(f'**Pago en efectivo {tipo}:** {first.porcentaje_efectivo:.2f}% en 2024, {d.loc[2025].porcentaje_efectivo:.2f}% en 2025 y {last.porcentaje_efectivo:.2f}% en 2026; cambio de {last.porcentaje_efectivo-first.porcentaje_efectivo:+.2f} puntos porcentuales. No se reasignan pagos ausentes o Flex Fare.')
        findings.append(f'**Cobertura de pasajeros {tipo}:** nulos {first.porcentaje_pasajeros_nulos:.2f}% → {d.loc[2025].porcentaje_pasajeros_nulos:.2f}% → {last.porcentaje_pasajeros_nulos:.2f}%. Un cambio puede reflejar composición o registro; no prueba que haya viajes sin pasajeros.')
        findings.append(f'**Total mediano {tipo}:** USD {first.total_mediano_usd:.2f} → {d.loc[2025].total_mediano_usd:.2f} → {last.total_mediano_usd:.2f}, en mediciones válidas. Es importe nominal, sin ajuste por inflación, rutas o cambios de cargos; no se atribuye causalidad.')
    report=['# Ejercicio 8: incorporación de 2025 y análisis de tres años',
        '## Descarga y preservación (8.1–8.2)',
        f"Conjunto validado: {len(paths)} Parquet, {validation['total_registros_metadata']:,} registros. Se preservaron {len(preserved)} archivos anteriores en bytes, mtime y SHA-256.",
        '```bash\ndocker compose exec -T lab python scripts/complete_three_years.py --snapshot\ndocker compose exec -T lab python scripts/download_data.py --years 2024 2025 2026 --verify-availability --manifest data/processed/download_manifest_2024_2025_2026_inicial.json\ndocker compose exec -T lab python scripts/download_data.py --years 2024 2025 2026 --verify-availability\ndocker compose exec -T lab python scripts/validate_download.py --manifest data/processed/download_manifest_2024_2025_2026.json --require-full-years 2024 2025\ndocker compose exec -T lab python scripts/complete_three_years.py\n```',
        'El snapshot debe crearse antes de ampliar y se conserva si existe. Los manifiestos inicial y repetido registran archivos descargados/omitidos; los datos y snapshots locales no se incluyen en Git.',
        '## Cobertura y compatibilidad (8.3)',table(frames['01_cobertura']),
        f'Se ejecutaron {len(checks)} verificaciones de SQL/selección: EDA, consultas representativas del benchmark e indicadores en cada año. Los CSV están en resultados_ejercicio_8/ y no sustituyen los resultados históricos de los ejercicios anteriores.',
        '## Indicadores y tablero (8.4)',
        'La nueva instantánea inmutable de tres años contiene la misma tabla viajes_duckdb. docs/tablero/indicadores.json selecciona su ruta; scripts/metabase_dashboard.py actualiza la conexión sin duplicar tablero o tarjetas. La instantánea y los tiempos originales del benchmark se conservan. Para actualizar Metabase, utilice la sesión local existente y ejecute el instalador de nuevo; se conecta siempre en read_only.',
        '## Evolución comparable (8.5)',
        'La comparación utiliza solo meses presentes en todos los años y ambos tipos. La demanda incluye recogidas coherentes con su mes; perfiles/costos agregan los filtros de medición del ejercicio 4. Se normaliza por días calendario, no se comparan los totales de 12 meses con un año parcial. La consulta 03 declara la selección y denominadores.',table(common.round(4)),
        '![Evolución mensual](figuras_ejercicio_8/demanda_tres_anios.png)',
        '![Período común](figuras_ejercicio_8/comparacion_periodo_comun.png)',
        '## Cambios y patrones (8.6)',*[f'{i}. {text}' for i,text in enumerate(findings,1)],
        'Las variaciones de medianas son aproximadas. Los datos observados no identifican causalidad; composición de viajes, cobertura y registro pueden variar. Los importes no están ajustados por inflación y los meses de 2026 todavía no publicados no se tratan como cero.',
        '## Consultas documentadas (8.7)']
    for p in sorted((ROOT/'sql'/'evolucion').glob('*.sql')):
        report.append(f'[{p.name}](../sql/evolucion/{p.name}): [resultado](resultados_ejercicio_8/{p.stem}.csv). Fuente: instantánea de los Parquet validados; año y mes proceden del archivo. 01 describe cobertura; 02 evolución mensual; 03 comparación en meses comunes; 04 perfil horario por año.')
    (ROOT/'docs'/'ejercicio_8_tres_anios.md').write_text('\n\n'.join(report)+'\n')
    print('Ejercicio 8 calculado:',config['database_file'],flush=True)
    return frames


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--snapshot',action='store_true');args=parser.parse_args()
    os.chdir(ROOT)
    if args.snapshot:snapshot()
    else:complete()


if __name__=='__main__':main()
