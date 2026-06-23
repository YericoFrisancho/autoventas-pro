import numpy_financial as npf

def generar_cronograma_credito(precio_vehiculo, cuota_inicial_porc, tea, plazo_meses,
                               porcentaje_balon, tipo_gracia, meses_gracia,
                               seg_desgravamen_porc, seg_vehicular_porc, seguros_opcionales,
                               cok_anual): 
    
    # Fase 1: Conversión de Tasas (Datos de entrada se mantienen con su precisión original para la tasa del periodo)
    tep = (1 + tea)**(30/360) - 1 
    cok_mensual = (1 + cok_anual)**(30/360) - 1
    
    # Fase 2: Estructuración de la Deuda
    # Resultados de salida que se usan en cálculos: se fijan a 2 decimales inmediatamente
    capital_inicial = round(precio_vehiculo * (1 - cuota_inicial_porc), 2)
    cuota_balon = round(precio_vehiculo * porcentaje_balon, 2)
    
    # Seguros fijos (Cálculo de salida a 2 decimales)
    monto_desgravamen_fijo = round(capital_inicial * seg_desgravamen_porc, 2)
    monto_vehicular_fijo = round((precio_vehiculo * seg_vehicular_porc) / 12, 2)
    total_seguros_mensuales = round(monto_desgravamen_fijo + monto_vehicular_fijo + seguros_opcionales, 2)
    
    saldo_vigente = capital_inicial
    cronograma = []
    flujos_caja = [capital_inicial] 
    
    # Fase 3 y 4: Método francés con dependencia estricta de 2 decimales en cadena
    for t in range(1, plazo_meses + 1): 
        saldo_inicial_t = saldo_vigente
        
        # El interés se calcula y se redondea a 2 decimales ANTES de usarse para cualquier otra cosa
        interes_t = round(saldo_vigente * tep, 2)
        
        if t <= meses_gracia and tipo_gracia != 'NINGUNO':
            if tipo_gracia == 'TOTAL':
                cuota_base_t = 0.0 
                amortizacion_t = 0.0 
                seguros_t = 0.0       
                pago_total_t = 0.0    
                # Usamos el interes_t ya redondeado para el nuevo saldo
                saldo_vigente = round(saldo_vigente + interes_t, 2) 
            elif tipo_gracia == 'PARCIAL':
                cuota_base_t = interes_t 
                amortizacion_t = 0.0 
                seguros_t = 0.0       
                pago_total_t = cuota_base_t  
        else:
            plazo_r = plazo_meses - t + 1 
            seguros_t = total_seguros_mensuales 
            
            # Cuota teórica base y se redondea inmediatamente
            cuota_teorica = (saldo_vigente - cuota_balon * (1 + tep)**(-plazo_r)) / ((1 - (1 + tep)**(-plazo_r)) / tep)
            cuota_base_t = round(cuota_teorica, 2)
            
            # La amortización DEPENDE de la cuota_base_t e interes_t estrictamente redondeados
            amortizacion_t = round(cuota_base_t - interes_t, 2) 
            # El saldo final DEPENDE de la amortización_t redondeada
            saldo_vigente = round(saldo_vigente - amortizacion_t, 2)
            # El pago total DEPENDE de cuota_base_t redondeada
            pago_total_t = round(cuota_base_t + seguros_t, 2)
            
        if t == plazo_meses: 
            cuota_base_t = round(cuota_base_t + cuota_balon, 2)
            pago_total_t = round(pago_total_t + cuota_balon, 2)
            amortizacion_t = round(amortizacion_t + cuota_balon, 2)
            saldo_vigente = 0.00            
            
        cronograma.append({
            'periodo': t,
            'tipo_gracia': tipo_gracia if t <= meses_gracia else 'NINGUNO',
            'saldo_inicial': saldo_inicial_t,
            'interes': interes_t,
            'cuota': cuota_base_t,
            'amortizacion': amortizacion_t,
            'seguros': seguros_t, 
            'pago_total': pago_total_t,
            'saldo_final': saldo_vigente
        })
        
        flujos_caja.append(-pago_total_t)
        
    # Fase 5: Evaluación Financiera
    # VAN redondeado a 2 decimales
    van = round(float(npf.npv(cok_mensual, flujos_caja)), 2)
    
    # TIR calculada, se guarda como resultado con 4 decimales (que equivale a 2 decimales porcentuales, ej. 0.0152 -> 1.52%)
    tir_mensual = round(float(npf.irr(flujos_caja)), 4)
    
    # TCEA calculada DEPENDIENDO de la TIR ya redondeada, y también se redondea a 4 decimales (2 en porcentaje)
    tcea = round(float(((1 + tir_mensual)**12) - 1), 4) 
    
    resultados_financieros = {
        'tcea': tcea,
        'van': van,
        'tir': tir_mensual,
        'total_pagado': round(sum(c['pago_total'] for c in cronograma), 2),
        'intereses_totales': round(sum(c['interes'] for c in cronograma), 2)
    }
    
    return cronograma, resultados_financieros