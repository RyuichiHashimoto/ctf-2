import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AttackPathService } from '../../services/attack-path.service';

@Component({
  selector: 'app-attack-inputs-panel',
  imports: [CommonModule, FormsModule],
  templateUrl: './attack-inputs-panel.component.html'
})
export class AttackInputsPanelComponent {
  constructor(public readonly service: AttackPathService) {}

  ensureTacticsLoaded(): void {
    if (this.service.mitreTactics.length === 0) {
      void this.service.loadTactics();
    }
  }

  onEntryPointChange(value: string): void {
    this.service.setEntryPoint(value);
  }

  onAttackTacticChange(value: string): void {
    this.service.setAttackTactic(value);
  }

  onAttackTechniqueChange(value: string): void {
    this.service.setAttackTechnique(value);
  }

  onAttackDataChange(value: string): void {
    this.service.setAttackData(value);
  }
}
