import numpy_financial as npf

def generar_cronograma_credito(precio_vehiculo, cuota_inicial_porc, tea, plazo_meses,
                               porcentaje_balon, tipo_gracia, meses_gracia,
                               seg_desgravamen_porc, seg_vehicular_porc, seguros_opcionales,
                               cok_mensual=0.015): 
    
    # Fase 1: Conversión de Tasas (Base 30/360)
    tep = (1 + tea)**(30/360) - 1 
    
    # Fase 2: Estructuración de la Deuda
    capital_inicial = float(precio_vehiculo * (1 - cuota_inicial_porc))
    cuota_balon = float(precio_vehiculo * porcentaje_balon)
    
    # Cálculo de Seguros Fijos
    monto_desgravamen_fijo = float(capital_inicial * seg_desgravamen_porc)
    monto_vehicular_fijo = float((precio_vehiculo * seg_vehicular_porc) / 12)
    total_seguros_mensuales = float(monto_desgravamen_fijo + monto_vehicular_fijo + seguros_opcionales)
    
    saldo_vigente = capital_inicial
    cronograma = []
    
    # Vector de flujos para calcular VAN y TIR (Momento 0 = ingreso del capital)
    flujos_caja = [capital_inicial] 
    
    # Fase 3 y 4: Generación del cronograma y método francés
    for t in range(1, plazo_meses + 1): 
        saldo_inicial_t = saldo_vigente
        interes_t = saldo_vigente * tep
        
        # Evaluación del Período de Gracia
        if t <= meses_gracia and tipo_gracia != 'NINGUNO':
            if tipo_gracia == 'TOTAL':
                cuota_base_t = 0.0 
                amortizacion_t = 0.0 
                pago_total_t = total_seguros_mensuales
                saldo_vigente += interes_t 
            elif tipo_gracia == 'PARCIAL':
                cuota_base_t = interes_t 
                amortizacion_t = 0.0 
                pago_total_t = cuota_base_t + total_seguros_mensuales
        else:
            # Cálculo normal (Fórmula francesa estándar ajustada)
            plazo_r = plazo_meses - t + 1 
            cuota_base_t = (saldo_vigente - cuota_balon * (1 + tep)**(-plazo_r)) / ((1 - (1 + tep)**(-plazo_r)) / tep) 
            amortizacion_t = cuota_base_t - interes_t 
            saldo_vigente -= amortizacion_t 
            
            pago_total_t = cuota_base_t + total_seguros_mensuales
            
        # Condición Lógica de Cierre
        if t == plazo_meses: 
            cuota_base_t += cuota_balon 
            pago_total_t += cuota_balon
            
        # Registrar línea del cronograma (Asegurando que todo sea float nativo)
        cronograma.append({
            'periodo': t,
            'tipo_gracia': tipo_gracia if t <= meses_gracia else 'NINGUNO',
            'saldo_inicial': float(saldo_inicial_t),
            'interes': float(interes_t),
            'cuota': float(cuota_base_t),
            'amortizacion': float(amortizacion_t),
            'seguros': float(total_seguros_mensuales), 
            'pago_total': float(pago_total_t),
            'saldo_final': float(saldo_vigente)
        })
        
        flujos_caja.append(-float(pago_total_t))
        
    # Fase 5: Evaluación Financiera
    van = float(npf.npv(cok_mensual, flujos_caja))
    tir_mensual = float(npf.irr(flujos_caja))
    tcea = float(((1 + tir_mensual)**12) - 1)
    
    resultados_financieros = {
        'tcea': tcea,
        'van': van,
        'tir': tir_mensual,
        'total_pagado': float(sum(c['pago_total'] for c in cronograma)),
        'intereses_totales': float(sum(c['interes'] for c in cronograma))
    }
    
    return cronograma, resultados_financieros