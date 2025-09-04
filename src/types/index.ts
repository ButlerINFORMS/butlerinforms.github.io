export interface Member {
    id: number;
    name: string;
    email: string;
    role: 'student' | 'officer';
}

export interface Event {
    id: number;
    title: string;
    date: string;
    location: string;
    description: string;
}

export interface Chapter {
    name: string;
    members: Member[];
    events: Event[];
}