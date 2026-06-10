import os
import psycopg2
import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash
from dotenv import load_dotenv
from calculos import generar_cronograma_credito

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'clave_secreta_para_autoventas_muy_segura')

def get_db_connection():
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )
    return conn

def ejecutar_migracion_estructural():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('ALTER TABLE creditos ALTER COLUMN seguro_desgravamen TYPE DECIMAL(8,6);')
        cur.execute('ALTER TABLE creditos ALTER COLUMN seguro_vehicular_porc TYPE DECIMAL(8,6);')
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Nota sobre migración estructural de tipos: {e}")

# NUEVO: La ruta raíz ahora muestra tu Landing Page de Figma
@app.route('/')
def inicio():
    if 'usuario_id' in session:
        return redirect(url_for('simulador'))
    # Renderizamos la nueva pantalla en lugar de forzar el redirect a login
    return render_template('inicio.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'usuario_id' in session:
        return redirect(url_for('simulador'))
        
    if request.method == 'POST':
        correo = request.form['correo']
        contrasenia = request.form['contrasenia']
        
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('SELECT id_cliente, nombre FROM clientes WHERE correo = %s AND contrasenia = %s', (correo, contrasenia))
            cliente = cur.fetchone()
            cur.close()
            conn.close()
            
            if cliente:
                session['usuario_id'] = cliente[0]
                session['usuario_nombre'] = cliente[1]
                return redirect(url_for('simulador'))
            else:
                flash('Correo o contraseña incorrectos', 'danger')
        except Exception as e:
            flash(f'Error al conectar con la base de datos: {e}', 'danger')
            
    return render_template('login.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if 'usuario_id' in session:
        return redirect(url_for('simulador'))
        
    if request.method == 'POST':
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        dni = request.form['dni']
        correo = request.form['correo']
        contrasenia = request.form['contrasenia']
        
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('SELECT COALESCE(MAX(id_cliente), 0) + 1 FROM clientes')
            nuevo_id = cur.fetchone()[0]
            
            cur.execute(
                'INSERT INTO clientes (id_cliente, nombre, apellido, correo, contrasenia, dni) VALUES (%s, %s, %s, %s, %s, %s)',
                (nuevo_id, nombre, apellido, correo, contrasenia, dni)
            )
            conn.commit()
            cur.close()
            conn.close()
            
            flash('Registro exitoso. ¡Ya puedes iniciar sesión!', 'success')
            return redirect(url_for('login'))
            
        except psycopg2.IntegrityError:
            flash('El correo o el DNI ingresado ya se encuentran registrados.', 'danger')
        except Exception as e:
            flash(f'Error al registrar el usuario: {e}', 'danger')
            
    return render_template('registro.html')

@app.route('/simulador', methods=['GET', 'POST'])
def simulador():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
        
    cronograma = None
    resultados = None
    vehiculos = []
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT id_vehiculo, marca, modelo, anio, precio_venta FROM vehiculos ORDER BY marca')
        vehiculos = cur.fetchall()
        
        if request.method == 'POST':
            id_vehiculo = int(request.form['id_vehiculo'])
            cuota_inicial_porc = float(request.form['cuota_inicial']) / 100
            tea = float(request.form['tea']) / 100
            plazo = int(request.form['plazo'])
            porc_balon = float(request.form['porc_balon']) / 100
            tipo_gracia = request.form['tipo_gracia']
            meses_gracia = int(request.form['meses_gracia'])
            
            seg_desgravamen = float(request.form['seg_desgravamen']) / 100
            seg_vehicular = float(request.form['seg_vehicular']) / 100
            seg_opcional = float(request.form.get('seg_opcional', 0))
            
            cur.execute('SELECT precio_venta FROM vehiculos WHERE id_vehiculo = %s', (id_vehiculo,))
            precio = float(cur.fetchone()[0])
            
            cronograma, resultados = generar_cronograma_credito(
                precio, cuota_inicial_porc, tea, plazo, porc_balon,
                tipo_gracia, meses_gracia, seg_desgravamen, seg_vehicular, seg_opcional
            )
            
            cur.execute('SELECT COALESCE(MAX(id_credito), 0) + 1 FROM creditos')
            nuevo_id_credito = cur.fetchone()[0]
            
            fecha_actual = datetime.datetime.now()
            cuota_inicial_monto = precio * cuota_inicial_porc
            monto_prestamo = precio - cuota_inicial_monto
            
            cur.execute('''
                INSERT INTO creditos 
                (id_credito, id_cliente, id_vehiculo, fecha_prestamo, cuota_inicial, monto_prestamo, tasa_efectiva, plazo_meses, gracia_tipo, gracia_num_periodos, porcentaje_globo, seguro_desgravamen, seguro_vehicular_porc, seguro_protec_tarjetas)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (nuevo_id_credito, session['usuario_id'], id_vehiculo, fecha_actual, cuota_inicial_monto, monto_prestamo, tea, plazo, tipo_gracia, meses_gracia, porc_balon, seg_desgravamen, seg_vehicular, seg_opcional))
            
            tep = (1 + tea)**(30/360) - 1
            cur.execute('SELECT COALESCE(MAX(id_cronograma), 0) FROM cronograma')
            max_id_crono = cur.fetchone()[0]
            
            for fila in cronograma:
                max_id_crono += 1
                cur.execute('''
                    INSERT INTO cronograma
                    (id_cronograma, id_credito, periodo, tasa_periodo, tipo_gracia, saldo_inicial, interes, cuota, amortizacion, saldo_final)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (max_id_crono, nuevo_id_credito, fila['periodo'], tep, fila['tipo_gracia'], fila['saldo_inicial'], fila['interes'], fila['cuota'], fila['amortizacion'], fila['saldo_final']))
                
            cur.execute('SELECT COALESCE(MAX(id_resultado), 0) + 1 FROM resultado_credito')
            nuevo_id_res = cur.fetchone()[0]
            
            cur.execute('''
                INSERT INTO resultado_credito
                (id_resultado, id_credito, tcea, van, tir, total_pagado, intereses_totales)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (nuevo_id_res, nuevo_id_credito, resultados['tcea'], resultados['van'], resultados['tir'], resultados['total_pagado'], resultados['intereses_totales']))
            
            conn.commit()
            flash('Simulación procesada y guardada en la base de datos exitosamente.', 'success')
            
        cur.close()
        conn.close()
        
    except Exception as e:
        flash(f'Error de sistema: {e}', 'danger')
            
    return render_template('simulador.html', vehiculos=vehiculos, cronograma=cronograma, resultados=resultados, edit_mode=False)

@app.route('/editar/<int:id_credito>', methods=['GET', 'POST'])
def editar(id_credito):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
        
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute('SELECT id_credito FROM creditos WHERE id_credito = %s AND id_cliente = %s', (id_credito, session['usuario_id']))
        if not cur.fetchone():
            flash('No tienes permiso para editar este crédito.', 'danger')
            return redirect(url_for('historial'))

        if request.method == 'GET':
            cur.execute('SELECT id_vehiculo, marca, modelo, anio, precio_venta FROM vehiculos ORDER BY marca')
            vehiculos = cur.fetchall()

            cur.execute('''
                SELECT c.id_vehiculo, c.cuota_inicial, c.tasa_efectiva, c.plazo_meses,
                       c.porcentaje_globo, c.gracia_tipo, c.gracia_num_periodos, c.seguro_protec_tarjetas,
                       c.seguro_desgravamen, c.seguro_vehicular_porc, v.precio_venta
                FROM creditos c
                JOIN vehiculos v ON c.id_vehiculo = v.id_vehiculo
                WHERE c.id_credito = %s
            ''', (id_credito,))
            row = cur.fetchone()
            
            precio_vehiculo = float(row[10])
            cuota_inicial_monto = float(row[1])
            
            credito_edit = {
                'id_credito': id_credito,
                'id_vehiculo': row[0],
                'cuota_inicial_porc': (cuota_inicial_monto / precio_vehiculo) * 100,
                'tea': float(row[2]) * 100,
                'plazo': row[3],
                'porc_balon': float(row[4]) * 100,
                'tipo_gracia': row[5],
                'meses_gracia': row[6],
                'seg_opcional': float(row[7]),
                'seg_desgravamen': float(row[8]) * 100,
                'seg_vehicular': float(row[9]) * 100
            }
            
            cronograma, resultados = generar_cronograma_credito(
                precio_vehiculo, (cuota_inicial_monto / precio_vehiculo), float(row[2]), int(row[3]), 
                float(row[4]), row[5], int(row[6]), float(row[8]), float(row[9]), float(row[7])
            )
            
            cur.close()
            conn.close()
            return render_template('simulador.html', vehiculos=vehiculos, cronograma=cronograma, 
                                   resultados=resultados, edit_mode=True, credito_edit=credito_edit)
                                   
        elif request.method == 'POST':
            id_vehiculo = int(request.form['id_vehiculo'])
            cuota_inicial_porc = float(request.form['cuota_inicial']) / 100
            tea = float(request.form['tea']) / 100
            plazo = int(request.form['plazo'])
            porc_balon = float(request.form['porc_balon']) / 100
            tipo_gracia = request.form['tipo_gracia']
            meses_gracia = int(request.form['meses_gracia'])
            
            seg_desgravamen = float(request.form['seg_desgravamen']) / 100
            seg_vehicular = float(request.form['seg_vehicular']) / 100
            seg_opcional = float(request.form.get('seg_opcional', 0))
            
            cur.execute('SELECT precio_venta FROM vehiculos WHERE id_vehiculo = %s', (id_vehiculo,))
            precio = float(cur.fetchone()[0])
            
            cronograma, resultados = generar_cronograma_credito(
                precio, cuota_inicial_porc, tea, plazo, porc_balon,
                tipo_gracia, meses_gracia, seg_desgravamen, seg_vehicular, seg_opcional
            )
            
            cuota_inicial_monto = precio * cuota_inicial_porc
            monto_prestamo = precio - cuota_inicial_monto
            
            cur.execute('''
                UPDATE creditos
                SET id_vehiculo=%s, cuota_inicial=%s, monto_prestamo=%s, tasa_efectiva=%s, plazo_meses=%s,
                    gracia_tipo=%s, gracia_num_periodos=%s, porcentaje_globo=%s, seguro_protec_tarjetas=%s,
                    seguro_desgravamen=%s, seguro_vehicular_porc=%s
                WHERE id_credito=%s
            ''', (id_vehiculo, cuota_inicial_monto, monto_prestamo, tea, plazo, tipo_gracia, meses_gracia, porc_balon, seg_opcional, seg_desgravamen, seg_vehicular, id_credito))
            
            cur.execute('DELETE FROM cronograma WHERE id_credito = %s', (id_credito,))
            
            tep = (1 + tea)**(30/360) - 1
            cur.execute('SELECT COALESCE(MAX(id_cronograma), 0) FROM cronograma')
            max_id_crono = cur.fetchone()[0]
            
            for fila in cronograma:
                max_id_crono += 1
                cur.execute('''
                    INSERT INTO cronograma
                    (id_cronograma, id_credito, periodo, tasa_periodo, tipo_gracia, saldo_inicial, interes, cuota, amortizacion, saldo_final)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (max_id_crono, id_credito, fila['periodo'], tep, fila['tipo_gracia'], fila['saldo_inicial'], fila['interes'], fila['cuota'], fila['amortizacion'], fila['saldo_final']))
            
            cur.execute('''
                UPDATE resultado_credito
                SET tcea=%s, van=%s, tir=%s, total_pagado=%s, intereses_totales=%s
                WHERE id_credito=%s
            ''', (resultados['tcea'], resultados['van'], resultados['tir'], resultados['total_pagado'], resultados['intereses_totales'], id_credito))
            
            conn.commit()
            
            cur.execute('SELECT id_vehiculo, marca, modelo, anio, precio_venta FROM vehiculos ORDER BY marca')
            vehiculos = cur.fetchall()
            
            cur.close()
            conn.close()
            
            credito_edit = {
                'id_credito': id_credito,
                'id_vehiculo': id_vehiculo,
                'cuota_inicial_porc': float(request.form['cuota_inicial']),
                'tea': float(request.form['tea']),
                'plazo': plazo,
                'porc_balon': float(request.form['porc_balon']),
                'tipo_gracia': tipo_gracia,
                'meses_gracia': meses_gracia,
                'seg_opcional': seg_opcional,
                'seg_desgravamen': float(request.form['seg_desgravamen']),
                'seg_vehicular': float(request.form['seg_vehicular'])
            }
            
            flash('¡Cambios guardados con éxito! El nuevo cronograma e indicadores se han recalculado.', 'success')
            return render_template('simulador.html', vehiculos=vehiculos, cronograma=cronograma, 
                                   resultados=resultados, edit_mode=True, credito_edit=credito_edit)

    except Exception as e:
        flash(f'Error al modificar el crédito: {e}', 'danger')
        return redirect(url_for('historial'))

@app.route('/historial')
def historial():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
        
    historial_creditos = []
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
            SELECT c.id_credito, TO_CHAR(c.fecha_prestamo, 'DD/MM/YYYY HH24:MI'), v.marca, v.modelo, c.monto_prestamo, r.tcea, r.total_pagado
            FROM creditos c
            JOIN vehiculos v ON c.id_vehiculo = v.id_vehiculo
            JOIN resultado_credito r ON c.id_credito = r.id_credito
            WHERE c.id_cliente = %s
            ORDER BY c.fecha_prestamo DESC
        ''', (session['usuario_id'],))
        
        historial_creditos = cur.fetchall()
        cur.close()
        conn.close()
    except Exception as e:
        flash(f'Error al cargar el historial: {e}', 'danger')
        
    return render_template('historial.html', historial=historial_creditos)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    ejecutar_migracion_estructural() 
    app.run(debug=True)