"""Script to seed threat catalogue from Threat Catalogue.txt"""
import json
from pathlib import Path

def seed_threat_catalogue():
    """Parse Threat Catalogue.txt and generate SQL insert statements."""
    
    catalogue_file = Path(__file__).parent.parent.parent.parent / "Threat Catalogue.txt"
    
    # Threat catalogue entries extracted from the file
    threats = [
        {
            "catalogue_key": "malicious_code",
            "title": "Malicious Code/Software",
            "description": "Code in any part of a software system intended to cause undesired effects or damage, includes attack scripts, backdoors and malicious active content."
        },
        {
            "catalogue_key": "social_engineering_phishing",
            "title": "Social Engineering (Phishing)",
            "description": "Phishing scams are fraudulent attempts by cybercriminals to obtain private information."
        },
        {
            "catalogue_key": "mitm_eavesdropping",
            "title": "Man-in-the-middle attack/Eavesdropping",
            "description": "A type of cyberattack where a malicious actor intercepts a conversation between two parties and gains access to information."
        },
        {
            "catalogue_key": "password_cracking",
            "title": "Password Cracking/Credential/Access Management",
            "description": "The process of using various techniques to discover computer passwords or stealing computer-based information."
        },
        {
            "catalogue_key": "system_penetration_hacking",
            "title": "System Penetration/Hacking",
            "description": "An attempt to gain unauthorized access to the IT infrastructure by trying to exploit vulnerabilities."
        },
        {
            "catalogue_key": "dos_disruption",
            "title": "Disruption of Service Provider/Denial of Service",
            "description": "Partial or complete outage of service, termination of contract or forces of nature."
        },
        {
            "catalogue_key": "unauthorized_access",
            "title": "Unauthorized Access",
            "description": "When someone gains access to a website, program, server, service, or other system using someone else's account."
        },
        {
            "catalogue_key": "data_loss_leakage",
            "title": "Data Loss/Data Leakage",
            "description": "An error condition where information is destroyed by failures or neglect in storage, transmission, or processing."
        },
        {
            "catalogue_key": "insider_threats",
            "title": "Insider Threats",
            "description": "Individuals within the organization (employees, contractors, partners) who intentionally or unintentionally pose a risk to systems or data."
        },
        {
            "catalogue_key": "supply_chain_attacks",
            "title": "Supply Chain Attacks",
            "description": "Compromising a system through vulnerabilities in third-party vendors, partners, or software/hardware suppliers."
        },
        {
            "catalogue_key": "apt",
            "title": "Advanced Persistent Threats (APTs)",
            "description": "Sophisticated, targeted attacks by state-sponsored or highly skilled adversary groups that persist in a network for extended periods."
        },
        {
            "catalogue_key": "ransomware",
            "title": "Ransomware",
            "description": "Malware that encrypts files/systems and demands payment for decryption. May include data exfiltration threats."
        },
        {
            "catalogue_key": "zero_day",
            "title": "Zero-Day Exploits",
            "description": "Attacks using vulnerabilities unknown to the software vendor with no patches available."
        },
        {
            "catalogue_key": "web_app_attacks",
            "title": "Web Application Attacks",
            "description": "Such as SQL injection, cross-site scripting (XSS), and cross-site request forgery (CSRF) targeting web-based applications."
        },
        {
            "catalogue_key": "physical_breach",
            "title": "Physical Security Breaches",
            "description": "Unauthorized physical access to infrastructure that could compromise IT assets or data."
        },
        {
            "catalogue_key": "malware_removable_media",
            "title": "Malware Loaded Removable Media",
            "description": "Attacks via infected USB drives or portable storage devices introduced into secure environments."
        },
        {
            "catalogue_key": "misconfiguration",
            "title": "Misconfiguration and Weak Security Controls",
            "description": "Poorly configured systems, default credentials, or inadequate policies leading to vulnerabilities."
        },
        {
            "catalogue_key": "cloud_security",
            "title": "Cloud Security Threats",
            "description": "Risks associated with cloud infrastructure such as misconfigured cloud storage, account hijacking, or insecure APIs."
        },
        {
            "catalogue_key": "iot_ot_threats",
            "title": "IoT and OT System Threats",
            "description": "Vulnerabilities and attacks targeting Internet-of-Things devices and operational technology environments."
        },
    ]
    
    # Generate SQL insert statements for manual use
    sql_statements = []
    for threat in threats:
        sql = f"""
INSERT INTO threat_catalogue (id, tenant_id, catalogue_key, title, description, default_likelihood, default_impact, mitigations, created_at, updated_at)
VALUES (gen_random_uuid(), 'TENANT_ID_HERE', '{threat["catalogue_key"]}', '{threat["title"]}', '{threat["description"].replace("'", "''")}', 'Medium', 'Medium', '[]'::jsonb, NOW(), NOW());
"""
        sql_statements.append(sql)
    
    return sql_statements


if __name__ == "__main__":
    statements = seed_threat_catalogue()
    print("\n".join(statements))
    print(f"\n-- {len(statements)} threat catalogue entries generated")
    print("-- Replace 'TENANT_ID_HERE' with actual tenant UUID before executing")
