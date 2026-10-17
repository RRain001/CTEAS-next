c-----------------------------------------------------------------------
      program p7e_oracle
c-----------------------------------------------------------------------
c
c --- CTEAS P7E FORTRAN ORACLE DRIVER -- hand written for this test
c     harness. This file is NOT vendor source and is never used by the
c     model; it drives the UNMODIFIED vendor units extracted by
c     reference/p7e_source_anchor.py:
c       PFSAMP  (puff-to-receptor sampling integrals)
c       ERFDIF  (error-function difference used by PFSAMP)
c       WRTI1D / WRTR1D / WRTR2D  (dataset record writers)
c
c --- Input on stdin, list directed:
c     line 1: mode  1 = PFSAMP matrix, 2 = record writing
c     mode 1: icase xold yold xnew ynew xrec yrec sygu dist2
c             -> stdout: icase xi1 xi2
c     mode 2: nrecords, then per record
c                label ndathrb nsecb ndathre nsece nvalues
c             the values are generated as v(i) = 0.5*i - 3.25 and written
c             with the vendor record writers into p7e_oracle_records.bin
c             -> stdout: P7E_ORACLE_WRITE=PASS records=<n>
c-----------------------------------------------------------------------
      include 'params.puf'
c
      character*8 label
      character*80 token
      integer mode,ios,icase,nrec,i,k,nvalues,ndathrb,nsecb,ndathre,
     &        nsece
      real xold,yold,xnew,ynew,xrec,yrec,sygu,dist2,xi1,xi2
      real x1d(10000)
      integer idat(1)
c
      read(*,*,iostat=ios) mode
      if(ios.ne.0) stop 'P7E oracle: missing mode'
c
      if(mode.eq.1)then
 10      read(*,*,iostat=ios) icase,xold,yold,xnew,ynew,xrec,yrec,
     &        sygu,dist2
         if(ios.ne.0) goto 999
         call pfsamp(xold,yold,xnew,ynew,xrec,yrec,sygu,dist2,xi1,xi2)
         write(*,'(i8,2(1x,es20.12))') icase,xi1,xi2
         goto 10
      endif
c
c --- mode 2: write a record sequence with the vendor writers
      open(unit=71,file='p7e_oracle_records.bin',status='replace',
     &     form='unformatted')
      read(*,*,iostat=ios) nrec
      if(ios.ne.0) stop 'P7E oracle: missing record count'
      do 100 k=1,nrec
         read(*,*,iostat=ios) token,ndathrb,nsecb,ndathre,nsece,nvalues
         if(ios.ne.0) stop 'P7E oracle: missing record description'
         label=token(1:8)
         do 90 i=1,nvalues
            x1d(i)=0.5*float(i)-3.25
 90      continue
         if(nvalues.eq.0)then
            call wrti1d(71,idat,0,label,ndathrb,nsecb,ndathre,nsece)
         elseif(nvalues.le.10000)then
            call wrtr1d(71,x1d,nvalues,label,ndathrb,nsecb,ndathre,
     &           nsece)
         else
            stop 'P7E oracle: record too large'
         endif
 100  continue
      close(unit=71)
      write(*,'(a,i8)') 'P7E_ORACLE_WRITE=PASS records=',nrec
      goto 999
c
 999  continue
      end
