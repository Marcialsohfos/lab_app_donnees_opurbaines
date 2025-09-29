from flask import Flask, jsonify, request, send_file, send_from_directory
from flask_cors import CORS
import pandas as pd
import os
from werkzeug.utils import secure_filename
import base64
import logging
import unicodedata

##### Début de configuration logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

os.makedirs(os.path.join(UPLOAD_FOLDER, 'troncons'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'taudis'), exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class IndicateursManager:
    def __init__(self, excel_path):
        self.excel_path = excel_path
        self.df = self.load_data()
    
    def load_data(self):
        """Charge les données depuis le fichier Excel avec nettoyage des colonnes"""
        try:
            if os.path.exists(self.excel_path):
                df = pd.read_excel(self.excel_path)
                print(f"Données chargées avec succès. {len(df)} lignes trouvées.")
                print(f"Colonnes: {df.columns.tolist()}")
                
                # Nettoyer les noms de colonnes
                df.columns = df.columns.str.strip()
                
                # Créer les colonnes images si elles n'existent pas
                if 'image_troncon' not in df.columns:
                    df['image_troncon'] = ''
                if 'image_taudis' not in df.columns:
                    df['image_taudis'] = ''
                    
                return df
            else:
                print("Fichier Excel non trouvé. Utilisation des données d'exemple.")
                return self.create_sample_data()
        except Exception as e:
            print(f"Erreur lors du chargement: {e}")
            return self.create_sample_data()
    
    def create_sample_data(self):
        """Crée des données d'exemple"""
        sample_data = {
            'Ville': ['Douala', 'Douala', 'Yaoundé', 'Yaoundé'],
            'Nom de la Commune': ['Douala 1', 'Douala 2', 'Yaoundé 1', 'Yaoundé 2'],
            'tronçon de voirie': ['Boulevard 1', 'Rue 2', 'Avenue 3', 'Boulevard 4'],
            'linéaire de voirie(ml)': [2500, 1200, 3200, 1800],
            'Nom de la poche du quartier de taudis': ['Quartier A', 'Quartier B', 'Quartier C', 'Quartier D'],
            'superficie de la poche du quartier de taudis': [12500, 8500, 9800, 7600],
            'présence du nid de poule': ['Oui', 'Non', 'Oui', 'Non'],
            'classe de voirie': ['Primaire', 'Secondaire', 'Primaire', 'Secondaire'],
            'Nombre de point lumineux sur le tronçon': [45, 28, 62, 35],
            'image_troncon': ['', '', '', ''],
            'image_taudis': ['', '', '', '']
        }
        return pd.DataFrame(sample_data)
    
    def remove_accents(self, text):
        """Supprime les accents d'un texte pour la normalisation"""
        if pd.isna(text):
            return ""
        text_str = str(text)
        return ''.join(c for c in unicodedata.normalize('NFD', text_str) 
                      if unicodedata.category(c) != 'Mn')
    
    def normaliser_texte(self, texte):
        """Normalise le texte pour la comparaison"""
        if pd.isna(texte):
            return ""
        texte_str = str(texte).strip().lower()
        return self.remove_accents(texte_str)
    
    def formater_nom_ville(self, ville):
        """Formate le nom de la ville pour l'affichage"""
        if pd.isna(ville):
            return "Non spécifiée"
        
        ville_normalisee = self.normaliser_texte(ville)
        
        if ville_normalisee == 'yaounde':
            return 'Yaoundé'
        elif ville_normalisee == 'douala':
            return 'Douala'
        else:
            return str(ville).strip().title()
    
    def get_villes(self):
        """Retourne la liste des villes disponibles"""
        villes = self.df['Ville'].dropna().unique()
        villes_formatees = [self.formater_nom_ville(ville) for ville in villes]
        return sorted(list(set(villes_formatees)))
    
    def get_communes(self, ville):
        """Retourne les communes d'une ville donnée (version simplifiée et robuste)"""
        print(f"DEBUG 🏙️ Ville demandée : '{ville}'")
        
        if not ville:
            return []
        
        # Normaliser la ville recherchée
        ville_recherchee = self.normaliser_texte(ville)
        print(f"DEBUG 🏙️ Ville normalisée pour recherche : '{ville_recherchee}'")
        
        # Normaliser toutes les villes pour la comparaison (sans créer de colonne)
        mask = self.df['Ville'].apply(self.normaliser_texte) == ville_recherchee
        communes = self.df.loc[mask, 'Nom de la Commune'].dropna().unique().tolist()
        
        print(f"DEBUG 🏘️ Communes trouvées pour {ville}: {communes}")
        return sorted(communes)
    
    def convertir_virgule_en_float(self, valeur):
        """Convertit les nombres avec virgule en float"""
        try:
            if pd.isna(valeur):
                return 0.0
            if isinstance(valeur, (int, float)):
                return float(valeur)
            return float(str(valeur).replace(',', '.').strip())
        except (ValueError, TypeError):
            return 0.0
    
    def clean_nan_values(self, obj):
        """Nettoie récursivement les valeurs NaN pour la sérialisation JSON"""
        if isinstance(obj, (int, float)):
            return obj if not pd.isna(obj) else None
        elif isinstance(obj, str):
            return obj
        elif isinstance(obj, dict):
            return {k: self.clean_nan_values(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.clean_nan_values(item) for item in obj]
        elif pd.isna(obj):
            return None
        else:
            return obj
    
    def calculer_stats_generales(self, data):
        """Calcule les statistiques générales"""
        try:
            data = data.copy()
            data['linéaire_ml_numeric'] = data['linéaire de voirie(ml)'].apply(self.convertir_virgule_en_float)
            data['superficie_numeric'] = data['superficie de la poche du quartier de taudis'].apply(self.convertir_virgule_en_float)
            data['points_lumineux_numeric'] = data['Nombre de point lumineux sur le tronçon'].apply(self.convertir_virgule_en_float)

            stats = {
                'nombre_troncons': len(data),
                'total_lineaire_ml': float(data['linéaire_ml_numeric'].sum(skipna=True)),
                'total_superficie_taudis': float(data['superficie_numeric'].sum(skipna=True)),
                'moyenne_points_lumineux': float(data['points_lumineux_numeric'].mean(skipna=True)) if not data['points_lumineux_numeric'].isna().all() else 0
            }
            return stats
        except Exception as e:
            print(f"Erreur dans calculer_stats_generales: {e}")
            return {'nombre_troncons': 0, 'total_lineaire_ml': 0, 'total_superficie_taudis': 0, 'moyenne_points_lumineux': 0}
    
    def analyser_classes_voirie(self, data):
        """Analyse la répartition des classes de voirie"""
        try:
            data_clean = data['classe de voirie'].fillna('Non spécifiée')
            return data_clean.value_counts().to_dict()
        except:
            return {}
    
    def analyser_nids_poule(self, data):
        """Analyse la présence de nids de poule"""
        try:
            data_clean = data['présence du nid de poule'].fillna('Non spécifié')
            return data_clean.value_counts().to_dict()
        except:
            return {'Non spécifié': len(data)}
    
    def preparer_troncons_voirie(self, data):
        """Prépare les données des tronçons de voirie"""
        troncons = []
        for _, row in data.iterrows():
            # Gérer les valeurs NaN 
            quartier=row.get('Nom de la poche du quartier de taudis','quartier non disponible')
            if pd.isna(quartier):
                quartier='quartier non disponible'
            nom = row.get('tronçon de voirie', 'Nom non disponible')
            if pd.isna(nom):
                nom = 'Nom non disponible'
            classe = row.get('classe de voirie', 'Non spécifiée')
            if pd.isna(classe):
                classe = 'Non spécifiée'
                
            nid_poule = row.get('présence du nid de poule', 'Non spécifié')
            if pd.isna(nid_poule):
                nid_poule = 'Non spécifié'
                
            image = row.get('image_troncon', '')
            if pd.isna(image):
                image = ''
            
            troncon = {
                'quartier': quartier,
                'nom': nom,
                'lineaire_ml': self.convertir_virgule_en_float(row.get('linéaire de voirie(ml)', 0)),
                'classe': classe,
                'nid_poule': nid_poule,
                'points_lumineux': self.convertir_virgule_en_float(row.get('Nombre de point lumineux sur le tronçon', 0)),
                'image': image
            }
            troncons.append(troncon)
        return troncons
    
    def preparer_quartiers_taudis(self, data):
        """Prépare les données des quartiers de taudis"""
        try:
            colonne_superficie = 'superficie de la poche du quartier de taudis'
            
            # Vérifier que les colonnes existent
            colonnes_necessaires = ['Nom de la poche du quartier de taudis', colonne_superficie, 'image_taudis']
            for col in colonnes_necessaires:
                if col not in data.columns:
                    print(f"⚠️ Colonne manquante: {col}")
                    return []
            
            taudis_data = data[colonnes_necessaires].dropna(subset=['Nom de la poche du quartier de taudis'])
            taudis_data = taudis_data.drop_duplicates()
            
            quartiers = []
            for _, row in taudis_data.iterrows():
                nom = row['Nom de la poche du quartier de taudis']
                if pd.isna(nom):
                    continue
                    
                image = row.get('image_taudis', '')
                if pd.isna(image):
                    image = ''
                
                quartier = {
                    'nom': nom,
                    'superficie_m2': self.convertir_virgule_en_float(row[colonne_superficie]),
                    'image': image
                }
                quartiers.append(quartier)
            return quartiers
        except Exception as e:
            print(f"Erreur dans preparer_quartiers_taudis: {e}")
            return []
    
    def get_indicateurs_commune(self, commune):
        """Récupère les indicateurs pour une commune (version simplifiée)"""
        print(f"DEBUG 🔍 Commune demandée : '{commune}'")

        if not commune:
            print("❌ Commune vide")
            return None

        # Normaliser la commune recherchée
        commune_cleaned = self.normaliser_texte(commune)
        print(f"DEBUG 🔍 Commune normalisée pour recherche : '{commune_cleaned}'")

        # Filtrer les données sans créer de colonne supplémentaire
        mask = self.df['Nom de la Commune'].apply(self.normaliser_texte) == commune_cleaned
        commune_data = self.df[mask]
        
        print(f"DEBUG 📊 {len(commune_data)} lignes trouvées pour cette commune")
        
        if len(commune_data) == 0:
            print(f"❌ Aucune donnée trouvée pour la commune '{commune}'")
            return None
        
        # Formater le nom de la ville pour l'affichage
        ville_formatee = self.formater_nom_ville(commune_data['Ville'].iloc[0])
        
        indicateurs = {
            'commune': commune,
            'ville': ville_formatee,
            'stats_generales': self.clean_nan_values(self.calculer_stats_generales(commune_data)),
            'troncons_voirie': self.clean_nan_values(self.preparer_troncons_voirie(commune_data)),
            'quartiers_taudis': self.clean_nan_values(self.preparer_quartiers_taudis(commune_data)),
            'analyse_classes_voirie': self.clean_nan_values(self.analyser_classes_voirie(commune_data)),
            'analyse_nids_poule': self.clean_nan_values(self.analyser_nids_poule(commune_data))
        }
        print("✅ Indicateurs générés avec succès")
        return indicateurs

# Initialisation
indicateurs_manager = IndicateursManager('indicateurs_urbains.xlsx')

# Routes pour les images
@app.route('/images/<image_type>/<filename>')
def serve_image(image_type, filename):
    if image_type not in ['troncons', 'taudis']:
        return jsonify({'error': 'Type d\'image invalide'}), 400
    try:
        return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER'], image_type), filename)
    except FileNotFoundError:
        return jsonify({'error': 'Image non trouvée'}), 404

@app.route('/api/upload/image', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return jsonify({'error': 'Aucun fichier envoyé'}), 400
    file = request.files['file']
    image_type = request.form.get('type', 'troncons')
    if file.filename == '':
        return jsonify({'error': 'Aucun fichier sélectionné'}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], image_type, filename)
        file.save(save_path)
        return jsonify({'message': 'Image uploadée avec succès', 'filename': filename})
    return jsonify({'error': 'Type de fichier non autorisé'}), 400

# Route de debug
@app.route('/api/debug/communes', methods=['GET'])
def debug_communes():
    """Debug spécifique pour les communes"""
    ville = request.args.get('ville', '')
    if not ville:
        return jsonify({'error': 'Paramètre "ville" manquant'}), 400

    # Normalisation identique à celle de votre code de recherche
    ville_cleaned = ville.strip().lower()
    if ville_cleaned in ['yaoundé', 'yaounde']:
        ville_cleaned = 'yaounde'

    # Filtrer le DataFrame
    communes = indicateurs_manager.df[indicateurs_manager.df['Ville'].str.strip().str.lower() == ville_cleaned]['Nom de la Commune'].dropna().unique().tolist()

    return jsonify({
        'ville_recherchee': ville,
        'ville_normalisee': ville_cleaned,
        'communes_disponibles': sorted(communes)
    })

@app.route('/api/debug', methods=['GET'])
def debug_data():
    """Route de debug pour voir les données"""
    debug_info = {
        'colonnes': indicateurs_manager.df.columns.tolist(),
        'villes_disponibles': indicateurs_manager.get_villes(),
        'premieres_lignes': indicateurs_manager.df.head(3).to_dict('records'),
        'communes_douala': indicateurs_manager.get_communes('Douala'),
        'communes_yaounde': indicateurs_manager.get_communes('Yaounde'),
        'communes_yaoundé': indicateurs_manager.get_communes('Yaoundé')
    }
    return jsonify(debug_info)

# Routes principales
@app.route('/')
def serve_frontend():
    try:
        return send_file('../frontend/index.html')
    except FileNotFoundError:
        try:
            return send_file('./frontend/index.html')
        except FileNotFoundError:
            return """
            <html>
                <body>
                    <h1>Application Indicateurs Urbains</h1>
                    <p>L'API Flask fonctionne correctement !</p>
                    <p><a href="/api/villes">Test API Villes</a></p>
                    <p><a href="/api/debug">Debug Data</a></p>
                </body>
            </html>
            """

@app.route('/api/villes', methods=['GET'])
def get_villes():
    villes = indicateurs_manager.get_villes()
    return jsonify(villes)

@app.route('/api/communes', methods=['GET'])
def get_communes():
    ville = request.args.get('ville')
    if not ville:
        return jsonify({'error': 'Paramètre ville manquant'}), 400
    communes = indicateurs_manager.get_communes(ville)
    return jsonify(communes)

@app.route('/api/indicateurs', methods=['GET'])
def get_indicateurs():
    commune = request.args.get('commune')
    logger.info(f"🌐 Requête API indicateurs pour la commune : {commune}")
    
    if not commune:
        logger.warning("❌ Paramètre 'commune' manquant dans la requête")
        return jsonify({'error': 'Paramètre commune manquant'}), 400
    
    try:
        indicateurs = indicateurs_manager.get_indicateurs_commune(commune)
        if indicateurs is None:
            logger.warning(f"🔍 Commune non trouvée : {commune}")
            return jsonify({'error': 'Commune non trouvée'}), 404
        
        logger.info(f"✅ Indicateurs envoyés pour {commune}")
        
        # Forcer le nettoyage avant sérialisation
        indicateurs_clean = indicateurs_manager.clean_nan_values(indicateurs)
        return jsonify(indicateurs_clean)
        
    except Exception as e:
        logger.error(f"Erreur critique dans /api/indicateurs: {e}")
        return jsonify({'error': f'Erreur interne du serveur: {str(e)}'}), 500

@app.route('/api/debug/commune-data', methods=['GET'])
def debug_commune_data():
    """Debug des données brutes d'une commune"""
    commune = request.args.get('commune')
    if not commune:
        return jsonify({'error': 'Paramètre commune manquant'}), 400
    
    # Normaliser la commune
    commune_cleaned = indicateurs_manager.normaliser_texte(commune)
    
    # Filtrer sans colonne supplémentaire
    mask = indicateurs_manager.df['Nom de la Commune'].apply(indicateurs_manager.normaliser_texte) == commune_cleaned
    commune_data = indicateurs_manager.df[mask]
    
    if len(commune_data) == 0:
        return jsonify({
            'erreur': 'Commune non trouvée',
            'commune_recherchee': commune,
            'commune_normalisee': commune_cleaned,
            'communes_disponibles': indicateurs_manager.df['Nom de la Commune'].unique().tolist()
        }), 404
    
    # Convertir en dict pour inspection
    raw_data = commune_data.to_dict('records')
    
    # Nettoyer les NaN pour l'affichage
    import math
    def clean_nan(obj):
        if isinstance(obj, float) and math.isnan(obj):
            return "NaN"
        return obj
    
    cleaned_data = []
    for record in raw_data:
        cleaned_record = {k: clean_nan(v) for k, v in record.items()}
        cleaned_data.append(cleaned_record)
    
    return jsonify({
        'commune_recherchee': commune,
        'commune_normalisee': commune_cleaned,
        'nombre_lignes': len(commune_data),
        'donnees_brutes': cleaned_data
    })


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
