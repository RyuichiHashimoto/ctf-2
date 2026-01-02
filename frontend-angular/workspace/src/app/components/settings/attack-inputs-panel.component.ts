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

  ensureScenariosLoaded(): void {
    if (this.service.attackScenarios.length === 0) {
      void this.service.loadAttackScenarios();
    }
  }

  onEntryPointChange(value: string): void {
    this.service.setEntryPoint(value);
  }

  onAttackScenarioChange(value: string): void {
    this.service.setAttackScenarioId(value);
  }

  onAttackDataChange(value: string): void {
    this.service.setAttackData(value);
  }
}
