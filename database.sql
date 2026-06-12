CREATE TABLE clientes (
    id_cliente INT PRIMARY KEY,
    nombre VARCHAR(20) NOT NULL,
    apellido VARCHAR(20) NOT NULL,
    correo VARCHAR(100) UNIQUE NOT NULL,
    contrasenia VARCHAR(20) NOT NULL,
    dni CHAR(8) UNIQUE NOT NULL
);

CREATE TABLE vehiculos (
    id_vehiculo INT PRIMARY KEY,
    marca VARCHAR(20) NOT NULL,
    modelo VARCHAR(20) NOT NULL,
    anio INT NOT NULL,
    tipo VARCHAR(20) NOT NULL,
    precio_venta DECIMAL(12,2) NOT NULL
);

CREATE TABLE creditos (
    id_credito INT PRIMARY KEY,
    id_cliente INT NOT NULL,
    id_vehiculo INT NOT NULL,
    fecha_prestamo TIMESTAMP NOT NULL,
    cuota_inicial DECIMAL(12,2) NOT NULL,
    monto_prestamo DECIMAL(12,2) NOT NULL,
    tasa_efectiva DECIMAL(7,4) NOT NULL,
    plazo_meses INT NOT NULL,
    gracia_tipo VARCHAR(10) NOT NULL,
    gracia_num_periodos INT NOT NULL,
    porcentaje_globo DECIMAL(5,2) NOT NULL,
    seguro_desgravamen DECIMAL(12,2) NOT NULL,
    seguro_vehicular_porc DECIMAL(12,2) NOT NULL,
    seguro_protec_tarjetas DECIMAL(12,2) NOT NULL,
    CONSTRAINT fk_credito_cliente FOREIGN KEY (id_cliente) REFERENCES clientes(id_cliente),
    CONSTRAINT fk_credito_vehiculo FOREIGN KEY (id_vehiculo) REFERENCES vehiculos(id_vehiculo)
);

CREATE TABLE cronograma (
    id_cronograma INT PRIMARY KEY,
    id_credito INT NOT NULL,
    periodo DECIMAL(8,6) NOT NULL,
    tasa_periodo DECIMAL(8,6) NULL,
    tipo_gracia VARCHAR(10) NOT NULL,
    saldo_inicial DECIMAL(14,2) NOT NULL,
    interes DECIMAL(14,2) NOT NULL,
    cuota DECIMAL(14,2) NOT NULL,
    amortizacion DECIMAL(14,2) NOT NULL,
    saldo_final DECIMAL(14,2) NOT NULL,
    CONSTRAINT fk_cronograma_credito FOREIGN KEY (id_credito) REFERENCES creditos(id_credito)
);

CREATE TABLE resultado_credito (
    id_resultado INT PRIMARY KEY,
    id_credito INT NOT NULL,
    tcea DECIMAL(7,4) NOT NULL,
    van DECIMAL(14,2) NOT NULL,
    tir DECIMAL(7,4) NOT NULL,
    total_pagado DECIMAL(14,2) NOT NULL,
    intereses_totales DECIMAL(14,2) NOT NULL,
    CONSTRAINT fk_resultado_credito FOREIGN KEY (id_credito) REFERENCES creditos(id_credito)
);