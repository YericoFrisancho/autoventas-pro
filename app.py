import os
import psycopg2
from flask import Flask, render_template, request, redirect, url_for, session, flash
from dotenv import load_dotenv
from calculos import generar_cronograma_credito

# Cargar las variables del archivo .env
load_dotenv()

app = Flask(__name__)
# Clave secreta obligatoria para el cifrado de sesiones y mensajes flash
app.secret_key = os.getenv('SECRET_KEY', 'clave_secreta_para_autoventas_muy_segura')

# Función para abrir la conexión a la base de datos PostgreSQL
def get_db_connection():
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )
    return conn

# Ruta raíz: Redirige automáticamente según el estado de la sesión
@app.route('/')
def inicio():
    if 'usuario_id' in session:
        return redirect(url_for('simulador'))
    return redirect(url_for('login'))

# Ruta de autenticación obligatoria
@app.route('/login', methods=['GET', 'POST'])
def login():
    # Si ya inició sesión, lo envía directo al simulador
    if 'usuario_id' in session:
        return redirect(url_for('simulador'))
        
    if request.method == 'POST':
        correo = request.form['correo']
        contrasenia = request.form['contrasenia']
        
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            # Validación de credenciales contra la base de datos relacional
            cur.execute('SELECT id_cliente, nombre FROM clientes WHERE correo = %s AND contrasenia = %s', (correo, contrasenia))
            cliente = cur.fetchone()
            cur.close()
            conn.close()
            
            if cliente:
                # Almacenar datos en la cookie cifrada de la sesión
                session['usuario_id'] = cliente[0]
                session['usuario_nombre'] = cliente[1]
                return redirect(url_for('simulador'))
            else:
                flash('Correo o contraseña incorrectos', 'danger')
        except Exception as e:
            flash(f'Error al conectar con la base de datos: {e}', 'danger')
            
    return render_template('login.html')

# Ruta de Registro de nuevos clientes
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
            
            # Generamos un ID autoincremental de forma manual basándonos en la tabla
            cur.execute('SELECT COALESCE(MAX(id_cliente), 0) + 1 FROM clientes')
            nuevo_id = cur.fetchone()[0]
            
            # Insertar los datos en la base de datos
            cur.execute(
                'INSERT INTO clientes (id_cliente, nombre, apellido, correo, contrasenia, dni) VALUES (%s, %s, %s, %s, %s, %s)',
                (nuevo_id, nombre, apellido, correo, contrasenia, dni)
            )
            conn.commit() # ¡Muy importante para guardar los cambios en la BD!
            cur.close()
            conn.close()
            
            flash('Registro exitoso. ¡Ya puedes iniciar sesión!', 'success')
            return redirect(url_for('login'))
            
        except psycopg2.IntegrityError:
            # Captura el error si el correo o el DNI ya existen (UNIQUE constraint)
            flash('El correo o el DNI ingresado ya se encuentran registrados.', 'danger')
        except Exception as e:
            flash(f'Error al registrar el usuario: {e}', 'danger')
            
    return render_template('registro.html')

# Ruta del Simulador de Crédito Vehicular (Protegida por sesión)
@app.route('/simulador', methods=['GET', 'POST'])
def simulador():
    # Validación de seguridad: Si no está logueado, rebota al login
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
        
    cronograma = None
    resultados = None
    
    if request.method == 'POST':
        try:
            # 1. Capturar los datos provenientes del formulario HTML
            precio = float(request.form['precio'])
            cuota_inicial = float(request.form['cuota_inicial']) / 100
            tea = float(request.form['tea']) / 100
            plazo = int(request.form['plazo'])
            porc_balon = float(request.form['porc_balon']) / 100
            tipo_gracia = request.form['tipo_gracia']
            meses_gracia = int(request.form['meses_gracia'])
            seg_opcional = float(request.form.get('seg_opcional', 0))
            
            # Constantes de seguros obligatorios fijos
            seg_desgravamen = 0.0005  # 0.05% mensual
            seg_vehicular = 0.03      # 3.00% anual
            
            # 2. Invocar la lógica financiera del modelo matemático
            cronograma, resultados = generar_cronograma_credito(
                precio, cuota_inicial, tea, plazo, porc_balon,
                tipo_gracia, meses_gracia, seg_desgravamen, seg_vehicular, seg_opcional
            )
        except Exception as e:
            flash(f'Error en el procesamiento de los cálculos: {e}', 'danger')
            
    return render_template('simulador.html', cronograma=cronograma, resultados=resultados)

# Ruta para destruir la sesión activa
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    # Ejecución en modo de depuración para desarrollo local
    app.run(debug=True)