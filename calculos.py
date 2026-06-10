import numpy_financial as npf

def generar_cronograma_credito(precio_vehiculo, cuota_inicial_porc, tea, plazo_meses,
                               porcentaje_balon, tipo_gracia, meses_gracia,
                               seg_desgravamen_porc, seg_vehicular_porc, seguros_opcionales,
                               cok_mensual=0.015): 
    
    # Fase 1: Conversión de Tasas (Base 30/360)
    tep = (1 + tea)**(30/360) - 1 
    
    # Fase 2: Estructuración de la Deuda
    capital_inicial = precio_vehiculo * (1 - cuota_inicial_porc) 
    cuota_balon = precio_vehiculo * porcentaje_balon 
    
    # === NUEVO CÁLCULO DE SEGUROS FIJOS ===
    # El desgravamen se calcula sobre el capital inicial para mantenerlo constante
    monto_desgravamen_fijo = capital_inicial * seg_desgravamen_porc 
    monto_vehicular_fijo = (precio_vehiculo * seg_vehicular_porc) / 12 
    total_seguros_mensuales = monto_desgravamen_fijo + monto_vehicular_fijo + seguros_opcionales
    
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
                cuota_base_t = 0 
                amortizacion_t = 0 
                # El seguro se sigue pagando o se suma al pago total
                pago_total_t = total_seguros_mensuales
                saldo_vigente += interes_t # Capitalización de intereses
            elif tipo_gracia == 'PARCIAL':
                cuota_base_t = interes_t # Solo se pagan intereses
                amortizacion_t = 0 
                pago_total_t = cuota_base_t + total_seguros_mensuales
        else:
            # Cálculo normal (Fórmula francesa estándar ajustada al saldo y tiempo restante)
            plazo_r = plazo_meses - t + 1 
            cuota_base_t = (saldo_vigente - cuota_balon * (1 + tep)**(-plazo_r)) / ((1 - (1 + tep)**(-plazo_r)) / tep) 
            amortizacion_t = cuota_base_t - interes_t 
            saldo_vigente -= amortizacion_t 
            
            # El pago total ahora es matemáticamente constante en cada periodo regular
            pago_total_t = cuota_base_t + total_seguros_mensuales
            
        # Condición Lógica de Cierre (Última cuota asume el pago globo)
        if t == plazo_meses: 
            cuota_base_t += cuota_balon 
            pago_total_t += cuota_balon
            
        # Registrar línea del cronograma
        cronograma.append({
            'periodo': t,
            'tipo_gracia': tipo_gracia if t <= meses_gracia else 'NINGUNO',
            'saldo_inicial': saldo_inicial_t,
            'interes': interes_t,
            'cuota': cuota_base_t,
            'amortizacion': amortizacion_t,
            'seguros': total_seguros_mensuales, # Ahora es siempre el mismo valor
            'pago_total': pago_total_t,
            'saldo_final': saldo_vigente
        })
        
        # El deudor desembolsa dinero (flujo negativo)
        flujos_caja.append(-pago_total_t)
        
    # Fase 5: Evaluación Financiera del Préstamo (Perspectiva del deudor)
    van = npf.npv(cok_mensual, flujos_caja) 
    tir_mensual = npf.irr(flujos_caja) 
    tcea = ((1 + tir_mensual)**12) - 1 
    
    resultados_financieros = {
        'tcea': tcea,
        'van': van,
        'tir': tir_mensual,
        'total_pagado': sum(c['pago_total'] for c in cronograma),
        'intereses_totales': sum(c['interes'] for c in cronograma)
    }
    
    return cronograma, resultados_financieros