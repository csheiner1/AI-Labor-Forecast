import openpyxl

wb = openpyxl.load_workbook('jobs-data-clean.xlsx', read_only=True, data_only=True)
ws = wb['2 Jobs']

rows = list(ws.iter_rows(values_only=True))

# Find Architecture & Engineering sector (sector 14) jobs for comparison
arch_eng_jobs = []
for row in rows[1:]:
    sector_id = str(row[3]) if row[3] is not None else ''
    if sector_id == '14':
        arch_eng_jobs.append(row)

print(f'Architecture & Engineering (Sector_ID=14) jobs: {len(arch_eng_jobs)}')
print()
print(f'{"Custom_Title":<45} {"SOC_Code":<12} {"Empl(K)":>9} {"Med_Wage":>10} {"Education":<30}')
print('-' * 110)
for row in arch_eng_jobs:
    soc_code   = str(row[0]) if row[0] else ''
    custom_title = str(row[2]) if row[2] else ''
    employment = row[7]
    median_wage = row[8]
    education  = str(row[9]) if row[9] else ''
    print(f'{custom_title:<45} {soc_code:<12} {str(employment):>9} {str(median_wage):>10} {education:<30}')

# Also check which SOC codes from Construction appear in other sectors
print()
print('=== Checking if Construction SOC codes appear elsewhere ===')
construction_socs = {'11-9021', '13-1051', '47-1011', '41-9091', '43-9061'}
for row in rows[1:]:
    soc = str(row[0]) if row[0] else ''
    sector_id = str(row[3]) if row[3] is not None else ''
    if soc in construction_socs and sector_id != '17':
        print(f'SOC {soc} | Custom_Title: {row[2]} | Sector: {row[4]} (ID={sector_id}) | Empl: {row[7]}')

print()
print('=== Total employment calculations for Construction ===')
construction_jobs = []
for row in rows[1:]:
    sector_id = str(row[3]) if row[3] is not None else ''
    if sector_id == '17':
        construction_jobs.append(row)

total_employment = 0
white_collar_employment = 0
WHITE_COLLAR_SOCS = {'11-9021', '13-1051'}  # Construction Manager, Construction Estimator

for row in construction_jobs:
    soc = str(row[0]) if row[0] else ''
    empl = row[7] if row[7] else 0
    educ = str(row[9]) if row[9] else ''
    custom_title = str(row[2]) if row[2] else ''
    try:
        empl_val = float(empl)
    except:
        empl_val = 0
    total_employment += empl_val
    if soc in WHITE_COLLAR_SOCS:
        white_collar_employment += empl_val
        print(f'White-collar: {custom_title} | SOC {soc} | Empl: {empl_val}K | Educ: {educ}')

print(f'\nTotal Construction employment (all 5 jobs): {total_employment:.1f}K')
print(f'White-collar Construction employment: {white_collar_employment:.1f}K')
print(f'White-collar % of Construction: {100*white_collar_employment/total_employment:.1f}%')
print(f'Blue-collar/clerical employment: {total_employment - white_collar_employment:.1f}K')

# Check all unique sectors in the dataset
print()
print('=== All sectors in dataset ===')
sectors = {}
for row in rows[1:]:
    sid = str(row[3]) if row[3] is not None else ''
    sname = str(row[4]) if row[4] is not None else ''
    if sid not in sectors:
        sectors[sid] = sname
for sid, sname in sorted(sectors.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 999):
    count = sum(1 for r in rows[1:] if str(r[3]) == sid)
    print(f'  Sector ID {sid}: {sname} ({count} jobs)')
