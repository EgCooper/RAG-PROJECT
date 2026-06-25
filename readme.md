### Laboratorios IA

### 1. Previous requirements for run laboratories

### 1.1 Virtual Enviroment

- python3 -m venv .venv

- source .venv/bin/activate


### 1.2 PIP Comands

- pip install upgrade pip

- pip install requests

- pip freeze > file.txt

### 1.3 Dependencies

#### Pdfs Extraction

![alt text](/imgs/image.png)

Para extraccion de pdfs tenemos las siguientes librerias pero para ambiente de pruebas y versiones gratuitas se pueden optar por las siguientes:

- PyMuPDF 
- Unstructured
- pdflumber

[:x] = Limitar la impresion de caracteres

[:] = Sin limite de impresion de caracteres

[How extract data of a pdf](extractor.py)

### Chunking

Dividir textos largos en fragmentos mas chicos para que modelos de LLMs y Embeddings puedan procesarlos

Estrategias de Chunking:

![alt text](/imgs/chunk.png)

Modelos disponibles para chunking gratis

![alt text](/imgs/chunkmodelsfree.png)

Modelos de pago

![alt text](/imgs/chunkmodelpayment.png)


2 puntos importantes en cuanto a chunking son los siguientes valores: 

Chunk-Size = define la cantidad de caracteres que imprimiremos 

Chunk-Overlap = es los caracteres final que traeremos del chunk pasado, esto con la finalidad de tener contexto

![alt text](/imgs/overlaps.png)

[How chunk data?](chunking.py)

### Embeddings

Representacion numerica del significado de un texto en forma de vector

El servicio cuesta $50"     →  [0.21, -0.54, 0.88, ...]

El precio es de $50"        →  [0.20, -0.51, 0.85, ...]  ← cercano (misma idea)

El clima está nublado hoy"  →  [0.95,  0.32, -0.41, ...] ← lejano (idea distinta)

Texto con significado similar producen vectores cercanos lo cual es util para busqueda semantica en RAG

Modelos Open Source

![alt text](/imgs/embeddingsfree.png)

Modelos de Paga

![alt text](/imgs/embeddingspayment.png)

Tokens = Unidad minima de texto que procesa el modelo, fragmentos

![alt text](/imgs/tokens.png)

Tokens = los tokens de un modelo define cuanto texto de entrada puede leer el modelo para generar ese array de dimensiones.

Dimensiones = Son la cantidad de numeros que compondran cada vector que genera el modelo

BGE-M3 genera vectores de 1024 dimensiones:

El servicio cuesta $50" → [0.21, -0.54, 0.88, 0.12, ... x1024 números]

text-embedding-3-large genera vectores de 3072 dimensiones:

El servicio cuesta $50" → [0.11, 0.73, -0.22, 0.95, ... x3072 números]

En resumen un modelo con mayor dimension contendra mas numero dentro de un vector lo cual 

[Embeddings](embedfing.py)

### Storage

El almacenamiento sera una base de datos vectorial ya que esta almacenan chunks,metadata,vectores lo cual permite que nuestro LLM pueda consultar sobre esta y entregar respuestas mas parecidas a la consulta que haga el user.

![alt text](/imgs/storage.png)

La seleccion sera weaviate ya que permite una busqueda hibrida avanzada y la escalabilidad es alta y es necesario por la gran cantidad de pdfs que manejaremos.

[Almacenamiento](storage.py)


### LLMs

Es un modelo de lenguaje entrenado con grandes volúmenes de texto capaz de entender y generar lenguaje natural. 

Es el componente final que recibe los chunks recuperados y redacta la respuesta al usuario

![alt text](/imgs/LLMs.png)

Parametros a configurar en nuestros prompts

![alt text](/imgs/parametersllm.png)

Mejor configuracion para nuestro asistente: 

![alt text](/imgs/settings.png)
