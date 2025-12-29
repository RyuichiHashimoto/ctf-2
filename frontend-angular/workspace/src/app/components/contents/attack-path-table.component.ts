import { Component, ChangeDetectorRef, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { combineLatest, Subscription } from 'rxjs';
import { AttackPathService } from '../../services/attack-path.service';

@Component({
  selector: 'app-attack-path-table',
  imports: [CommonModule],
  templateUrl: './attack-path-table.component.html'
})
export class AttackPathTableComponent implements OnInit, OnDestroy {
  private subscription?: Subscription;

  constructor(
    public readonly service: AttackPathService,
    private readonly cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.subscription = combineLatest([
      this.service.graphData$,
      this.service.predictedPaths$
    ]).subscribe(() => {
      this.cdr.detectChanges();
    });
  }

  ngOnDestroy(): void {
    this.subscription?.unsubscribe();
  }

  setSelectedPath(path: string[] | null): void {
    this.service.setSelectedPath(path);
  }

  trackByRowId(_: number, row: { id: number }): number {
    return row.id;
  }
}
