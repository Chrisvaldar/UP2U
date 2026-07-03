export type Restaurant = {
    name: string;
    reason: string;
    maps_link: string;
    photo_urls?: string[];
  };
  
export type RevealData = {
    personality_lines: Record<string, string>;
    agreements: string;
    conflicts: string;
    primary: Restaurant;
    backups: Restaurant[];
  };

export function saveParticipantName(code: string, name: string) {
    sessionStorage.setItem(`up2u:${code.toUpperCase()}:name`, name);
  }

export function getParticipantName(code: string){
    return sessionStorage.getItem(`up2u:${code.toUpperCase()}:name`)
}

export function saveReveal(code: string, reveal: RevealData){
    sessionStorage.setItem(`up2u:${code.toUpperCase()}:reveal`, JSON.stringify(reveal))
}

export function getReveal(code: string){
    const reveal = sessionStorage.getItem(`up2u:${code.toUpperCase()}:reveal`)
    if (!reveal){
        return
    }
    return JSON.parse(reveal) as RevealData;
}

export function clearReveal(code: string){
    sessionStorage.removeItem(`up2u:${code.toUpperCase()}:reveal`);
}

export type SurveyDraft = {
    step: number;
    hunger: number;
    vibe: string;
    cuisinesRanked: string[];
    travelDistance: string;
    dietary: string[];
};

export function saveDraft(code: string, draft: SurveyDraft) {
    sessionStorage.setItem(
        `up2u:${code.toUpperCase()}:draft`,
        JSON.stringify(draft),
    );
}

export function getDraft(code: string) {
    const draft = sessionStorage.getItem(`up2u:${code.toUpperCase()}:draft`);
    if (!draft) {
        return;
    }
    return JSON.parse(draft) as SurveyDraft;
}

export function clearDraft(code: string) {
    sessionStorage.removeItem(`up2u:${code.toUpperCase()}:draft`);
}

export function setFlashMessage(message: string) {
    sessionStorage.setItem("up2u:message", message);
}