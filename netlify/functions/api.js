// netlify/functions/api.js
const BACKEND_URL = 'https://lab-app-donnees-opurbaines.onrender.com';

exports.handler = async (event, context) => {
    console.log('📍 Fonction Netlify appelée:', event.path, event.httpMethod);
    
    const headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS'
    };

    // CORS preflight
    if (event.httpMethod === 'OPTIONS') {
        return { statusCode: 200, headers, body: '' };
    }

    try {
        // Proxy vers le backend Render
        const renderResponse = await fetch(`${BACKEND_URL}${event.path}${event.rawQuery ? '?' + event.rawQuery : ''}`, {
            method: event.httpMethod,
            headers: {
                'Content-Type': 'application/json',
            }
        });

        if (renderResponse.ok) {
            const data = await renderResponse.json();
            console.log('✅ Backend Render fonctionne');
            return {
                statusCode: 200,
                headers,
                body: JSON.stringify(data)
            };
        } else {
            throw new Error('Backend non disponible');
        }
    } catch (error) {
        console.log('🔄 Utilisation des données de secours:', error.message);
        
        // 🎯 DONNÉES DE SECOURS
        return getFallbackData(event, headers);
    }
};

function getFallbackData(event, headers) {
    // Routes de secours
    if (event.path === '/api/villes' || event.path === '/api/villes/') {
        return {
            statusCode: 200,
            headers,
            body: JSON.stringify(['Douala', 'Yaoundé'])
        };
    }

    if (event.path === '/api/communes' || event.path === '/api/communes/') {
        const ville = event.queryStringParameters?.ville || '';
        let communes = [];
        
        if (ville.toLowerCase().includes('douala')) {
            communes = ['Douala 1', 'Douala 2', 'Douala 3', 'Douala 4', 'Douala 5'];
        } else if (ville.toLowerCase().includes('yaound')) {
            communes = ['Yaoundé 1', 'Yaoundé 2', 'Yaoundé 3', 'Yaoundé 4', 'Yaoundé 5', 'Yaoundé 6', 'Yaoundé 7'];
        }
        
        return {
            statusCode: 200,
            headers,
            body: JSON.stringify(communes)
        };
    }

    if (event.path === '/api/indicateurs' || event.path === '/api/indicateurs/') {
        const commune = event.queryStringParameters?.commune || '';
        return {
            statusCode: 200,
            headers,
            body: JSON.stringify({
                commune: commune,
                ville: commune.includes('Douala') ? 'Douala' : 'Yaoundé',
                stats_generales: {
                    nombre_troncons: 12,
                    total_lineaire_ml: 15000,
                    total_superficie_taudis: 45000,
                    moyenne_points_lumineux: 35
                },
                troncons_voirie: [
                    {
                        quartier: "Quartier A",
                        nom: "Boulevard Principal",
                        lineaire_ml: 2500,
                        classe: "Primaire",
                        nid_poule: "Oui",
                        points_lumineux: 45,
                        image: ""
                    }
                ],
                quartiers_taudis: [
                    {
                        nom: "Quartier B",
                        superficie_m2: 12500,
                        image: ""
                    }
                ],
                analyse_classes_voirie: {
                    "Primaire": 8,
                    "Secondaire": 4
                },
                analyse_nids_poule: {
                    "Oui": 7,
                    "Non": 5
                }
            })
        };
    }

    if (event.path === '/api/health' || event.path === '/api/health/') {
        return {
            statusCode: 200,
            headers,
            body: JSON.stringify({
                status: 'healthy',
                message: 'Netlify Function active',
                backend: 'fallback'
            })
        };
    }

    return {
        statusCode: 404,
        headers,
        body: JSON.stringify({ error: 'Route non trouvée: ' + event.path })
    };
}