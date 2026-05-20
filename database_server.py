
import random

def get_central_production_lot():
    """
    Simule une base de données centrale de Dar As-Sikka 
    contenant une masse de données (Big Data - 5000 entrées) pour le PFE.
    """
    surnames = [
        "EL IDRISSI", "BENJELLOUN", "ALAMI", "TAZI", "CHRAIBI", "OUAZZANI", "BOURKADI", 
        "SEBTI", "AMRANI", "FILALI", "BOUNOU", "HAKIMI", "ZIYECH", "SAISS", "AMRABAT", 
        "OUNAHI", "BOUFAL", "EL KAABI", "MABROUK", "JABRANE", "CHERKAOUI", "BENNANI", 
        "MANSOURI", "GLAOUI", "SLAOUI", "FAASSI", "TAREK", "YOUSFI", "NACIRI", "KABBAJ"
    ]
    
    given_names = [
        "MALIKA", "YASSINE", "AMINE", "FATIMA", "MERIEM", "OMAR", "ANASS", "KHADIJA", 
        "MOHAMED", "ACHRAF", "REDA", "NAJAT", "SOFIANE", "GHITA", "HAMZA", "TARIK", 
        "YOUSEF", "LAYLA", "KAOUTAR", "ZINEB", "SOUAD", "IBRAHIM", "ADIL", "HALIMA", 
        "WARDA", "SAID", "MUSTAPHA", "NADA", "ANWAR", "HOUSSAM"
    ]
    
    big_data_lot = []
    
    # هنا السحر الحقيقي: 5000 سطر د الداتا ف السيرفر المركزي
    for i in range(1, 5001):
        num_pass = f"MA{random.randint(1000000, 9999999)}"
        score = round(random.uniform(98.0, 99.9), 2)
        nom = surnames[i % len(surnames)]
        prenom = given_names[i % len(given_names)]
        
        # توزيع التواريخ بين 2024 و 2026
        annee = random.choice([2024, 2025, 2026])
        mois = random.randint(1, 12)
        jour = random.randint(1, 28)
        date_prod = f"{annee}-{mois:02d}-{jour:02d}"
        
        big_data_lot.append({
            "ID_Document": f"DS-PASS-{i:04d}",
            "Numero_Passeport": num_pass,
            "Nom": nom,
            "Prenom": prenom,
            "Date_Production": date_prod,
            "Score_Precision_OCR": f"{score} %",
            "Statut_Conformite": "Conforme ✅"
        })
        
    return big_data_lot
