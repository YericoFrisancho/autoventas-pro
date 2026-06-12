from calculos import generar_cronograma_credito

cronograma, resultados = generar_cronograma_credito(
    precio_vehiculo=12000.00,
    cuota_inicial_porc=0.20,
    tea=0.15,
    plazo_meses=24,
    porcentaje_balon=0.30,
    tipo_gracia='PARCIAL',
    meses_gracia=4,
    seg_desgravamen_porc=0.0005, 
    seg_vehicular_porc=0.03,     
    seguros_opcionales=25.00,
    cok_mensual=0.015            
)

print("=== INDICADORES FINANCIEROS ===")
print(f"Cuota Base Constante (R): ${cronograma[4]['cuota']:.2f}") 
print(f"TIR Mensual: {resultados['tir'] * 100:.2f}%")
print(f"TCEA (Costo Real Anual): {resultados['tcea'] * 100:.2f}%")
print(f"VAN: ${resultados['van']:.2f}")
print(f"Total Pagado: ${resultados['total_pagado']:.2f}")