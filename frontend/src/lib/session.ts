export type Restaurant = {
    name: string;
    reason: string;
    maps_link: string;
  };
  
export type RevealData = {
    personality_lines: Record<string, string>;
    agreements: string;
    conflicts: string;
    primary: Restaurant;
    backups: Restaurant[];
  };

export function saveParticipantName(code: string, name: string) {
    sessionStorage.setItem(`up2u:${code}:name`, name);
  }

export function getParticipantName(code: string){
    return sessionStorage.getItem(`up2u:${code}:name`)
}

export function saveReveal(code: string, reveal: RevealData){
    sessionStorage.setItem(`up2u:${code}:reveal`, JSON.stringify(reveal))
}

export function getReveal(code: string){
    const reveal = sessionStorage.getItem(`up2u:${code}:reveal`)
    if (!reveal){
        return
    }
    return JSON.parse(reveal) as RevealData;
}

export function clearReveal(code: string){
    sessionStorage.removeItem(`up2u:${code}:reveal`);
}

export function setFlashMessage(message: string) {
    sessionStorage.setItem("up2u:message", message);
}